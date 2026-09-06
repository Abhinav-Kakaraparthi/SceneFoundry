from functools import partial

from google.cloud import firestore

from scenefoundry.agents.accounted import run_accounted
from scenefoundry.agents.execution import run_director
from scenefoundry.billing.rates import TokenRateCard
from scenefoundry.domain.scene import SceneSpec


async def generate_scene(
    db: firestore.Client,
    *,
    studio_project_id: str,
    attempt_id: str,
    brief: str,
    reservation_micro_usd: int,
    rate: TokenRateCard,
) -> SceneSpec:
    """Generate a scene with a reservation and durable response accounting."""
    brief = brief.strip()
    if not brief or len(brief) > 4000:
        raise ValueError("Brief must contain between 1 and 4000 characters.")

    return await run_accounted(
        db,
        studio_project_id=studio_project_id,
        attempt_id=attempt_id,
        reservation_micro_usd=reservation_micro_usd,
        rate=rate,
        execute=partial(run_director, brief, rate.model),
        validate=SceneSpec.model_validate_json,
    )
