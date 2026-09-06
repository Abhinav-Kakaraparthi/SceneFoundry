import logging

from fastapi import APIRouter, HTTPException
from google.api_core.exceptions import Conflict
from pydantic import BaseModel, ConfigDict, Field

from scenefoundry.agents.production import generate_scene
from scenefoundry.api.projects import Database, ResourceId
from scenefoundry.billing.rates import GEMINI_35_FLASH_GLOBAL_STANDARD
from scenefoundry.domain.scene import SceneSpec

router = APIRouter(prefix="/v1/projects", tags=["generation"])
logger = logging.getLogger(__name__)

DIRECTOR_RESERVATION_MICRO_USD = 50_000


class GenerateRequest(BaseModel):
    model_config = ConfigDict(
        strict=True, extra="forbid", str_strip_whitespace=True
    )

    attempt_id: str = Field(pattern=r"^[a-f0-9]{32}$")
    brief: str = Field(min_length=1, max_length=4000)


class GenerateResponse(BaseModel):
    attempt_id: str
    scene: SceneSpec


@router.post("/{project_id}/attempts", status_code=201)
async def submit_brief(
    project_id: ResourceId,
    request: GenerateRequest,
    db: Database,
) -> GenerateResponse:
    try:
        scene = await generate_scene(
            db,
            studio_project_id=project_id,
            attempt_id=request.attempt_id,
            brief=request.brief,
            reservation_micro_usd=DIRECTOR_RESERVATION_MICRO_USD,
            rate=GEMINI_35_FLASH_GLOBAL_STANDARD,
        )
    except Conflict as error:
        raise HTTPException(
            status_code=409,
            detail="A record already exists for this attempt. Inspect it before retrying.",
        ) from error
    except Exception as error:
        logger.exception(
            "Generation failed for project=%s attempt=%s",
            project_id,
            request.attempt_id,
        )
        raise HTTPException(
            status_code=500,
            detail="Generation did not complete. Keep this attempt ID for inspection.",
        ) from error

    return GenerateResponse(attempt_id=request.attempt_id, scene=scene)
