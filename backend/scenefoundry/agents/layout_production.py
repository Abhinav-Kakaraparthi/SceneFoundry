"""Accounted generation of a static layout for one validated shot."""

from functools import partial

from google.cloud import firestore

from scenefoundry.agents.accounted import run_accounted
from scenefoundry.agents.layout_execution import run_layout, validate_layout
from scenefoundry.billing.rates import TokenRateCard
from scenefoundry.domain.layout import ShotLayout
from scenefoundry.domain.shot import ShotSpec

# Initial application allowance, not a provider-enforced spending limit.
LAYOUT_RESERVATION_MICRO_USD = 150_000


async def generate_layout(
    db: firestore.Client,
    *,
    studio_project_id: str,
    attempt_id: str,
    shot: ShotSpec,
    rate: TokenRateCard,
) -> ShotLayout:
    """Save and settle the response before validating geometry and shot ID."""
    return await run_accounted(
        db,
        studio_project_id=studio_project_id,
        attempt_id=attempt_id,
        reservation_micro_usd=LAYOUT_RESERVATION_MICRO_USD,
        rate=rate,
        execute=partial(run_layout, shot, rate.model),
        validate=partial(validate_layout, expected_shot_id=shot.shot_id),
    )
