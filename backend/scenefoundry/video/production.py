"""Reserve application funds and submit a durable Veo attempt."""

import logging

from google.cloud import firestore

from scenefoundry.billing.veo import (
    MICRO_USD_PER_SECOND,
    RATE_ID,
    SOURCE_URL,
    estimate_veo_micro_usd,
)
from scenefoundry.storage.attempts import claim_attempt, create_attempt
from scenefoundry.storage.video_operations import save_video_operation
from scenefoundry.video.client import create_veo_client
from scenefoundry.video.submission import submit_veo
from scenefoundry.video.veo_config import (
    VEO_LOCATION,
    VEO_MODEL,
    build_veo_config,
)

logger = logging.getLogger(__name__)


def start_veo(
    db: firestore.Client,
    *,
    studio_project_id: str,
    attempt_id: str,
    prompt: str,
    duration_seconds: int = 4,
) -> str:
    """Submit a new attempt; leave its reservation pending completion."""
    if not isinstance(prompt, str) or not 1 <= len(prompt.strip()) <= 4000:
        raise ValueError("Video prompt must contain 1 to 4000 characters.")
    prompt = prompt.strip()
    config = build_veo_config(duration_seconds)
    estimate = estimate_veo_micro_usd(VEO_MODEL, VEO_LOCATION, config)
    identifiers = {
        "studio_project_id": studio_project_id,
        "attempt_id": attempt_id,
    }

    with create_veo_client(db.project) as client:
        create_attempt(db, **identifiers, model=VEO_MODEL)
        attempt = db.document(
            "projects", studio_project_id, "attempts", attempt_id
        )
        stage = "request_checkpoint"
        operation_name = None
        try:
            attempt.update(
                {
                    "kind": "veo_video",
                    "prompt": prompt,
                    "location": VEO_LOCATION,
                    "video_config": config.model_dump(
                        mode="json", exclude_none=True
                    ),
                    "estimated_cost_micro_usd": estimate,
                    "pricing_estimate": {
                        "rate_id": RATE_ID,
                        "micro_usd_per_second": MICRO_USD_PER_SECOND,
                        "source_url": SOURCE_URL,
                    },
                },
                timeout=15,
            )

            stage = "reservation"
            if not claim_attempt(
                db, **identifiers, reservation_micro_usd=estimate
            ):
                raise RuntimeError("Attempt was already claimed.")

            stage = "submission"
            operation_name = submit_veo(client, prompt, duration_seconds)

            stage = "operation_checkpoint"
            save_video_operation(attempt, operation_name)
            return operation_name
        except Exception as error:
            try:
                attempt.update(
                    {
                        "failure_stage": stage,
                        "error_type": type(error).__name__,
                    },
                    timeout=15,
                )
            except Exception:
                logger.exception("Could not record Veo attempt failure.")
            raise RuntimeError(
                f"Veo failed at {stage}; attempt={attempt_id}; "
                f"operation={operation_name!r}. Do not automatically resubmit."
            ) from error
