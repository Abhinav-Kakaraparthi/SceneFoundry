import asyncio
import os
from collections.abc import Awaitable, Callable
from typing import TypeVar

from google.cloud import firestore

from scenefoundry.billing.rates import TokenRateCard
from scenefoundry.billing.usage import price_director_usage
from scenefoundry.domain.director_grounding import (
    DirectorGrounding,
)
from scenefoundry.storage.attempts import claim_attempt, create_attempt
from scenefoundry.storage.responses import save_response
from scenefoundry.storage.settlement import settle_attempt

Result = TypeVar("Result")
Receipt = tuple[str, list[dict[str, object]]]


async def run_accounted(
    db: firestore.Client,
    *,
    studio_project_id: str,
    attempt_id: str,
    reservation_micro_usd: int,
    rate: TokenRateCard,
    grounding: DirectorGrounding | None = None,
    execute: Callable[[], Awaitable[Receipt]],
    validate: Callable[[str], Result],
) -> Result:
    """Persist and settle model usage before validating its output."""
    if os.environ.get("GOOGLE_CLOUD_PROJECT") != db.project:
        raise ValueError("Model and storage Cloud projects must match.")
    if os.environ.get("GOOGLE_CLOUD_LOCATION") != rate.location:
        raise ValueError("Model location must match the rate card.")
    if os.environ.get("GOOGLE_GENAI_USE_ENTERPRISE", "").lower() != "true":
        raise ValueError("Google Cloud model access must be enabled.")

    identifiers = {
        "studio_project_id": studio_project_id,
        "attempt_id": attempt_id,
    }
    await asyncio.to_thread(
        create_attempt,
        db,
        **identifiers,
        model=rate.model,
        grounding=grounding,
    )
    attempt = db.document(
        "projects", studio_project_id, "attempts", attempt_id
    )
    stage = "reservation"

    try:
        claimed = await asyncio.to_thread(
            claim_attempt,
            db,
            **identifiers,
            reservation_micro_usd=reservation_micro_usd,
        )
        if not claimed:
            raise RuntimeError("Attempt was already claimed.")

        stage = "generation"
        text, usage = await execute()

        stage = "response_checkpoint"
        await asyncio.to_thread(
            save_response, db, **identifiers, text=text, usage=usage
        )

        stage = "pricing"
        cost = price_director_usage(
            usage, model=rate.model, location=rate.location, rate=rate
        )

        stage = "settlement"
        await asyncio.to_thread(
            settle_attempt,
            db,
            **identifiers,
            cost_micro_usd=cost,
            rate=rate,
        )

        stage = "output_validation"
        result = validate(text)

        stage = "completion"
        await asyncio.to_thread(
            attempt.update,
            {
                "status": "succeeded",
                "completed_at": firestore.SERVER_TIMESTAMP,
            },
            timeout=15,
        )
        return result
    except Exception as error:
        await asyncio.to_thread(
            attempt.update,
            {
                "failure_stage": stage,
                "error_type": type(error).__name__,
            },
            timeout=15,
        )
        raise
