"""Authenticated, research-grounded Director generation API."""

import logging

from fastapi import APIRouter, HTTPException, status
from google.api_core.exceptions import Conflict
from pydantic import BaseModel, ConfigDict, Field

from scenefoundry.agents.production import generate_scene
from scenefoundry.api.auth import CurrentUser
from scenefoundry.api.projects import Database, ResourceId
from scenefoundry.billing.rates import GEMINI_35_FLASH_GLOBAL_STANDARD
from scenefoundry.domain.director_grounding import (
    DirectorGrounding,
    create_director_grounding,
)
from scenefoundry.domain.revision import (
    SceneRevision,
    build_scene_revision,
)
from scenefoundry.domain.scene import SceneSpec
from scenefoundry.storage.research import read_production_research
from scenefoundry.storage.revisions import save_scene_revision
from scenefoundry.storage.users import read_verified_user


router = APIRouter(prefix="/v1/projects", tags=["generation"])
logger = logging.getLogger(__name__)

DIRECTOR_RESERVATION_MICRO_USD = 50_000


class GenerateRequest(BaseModel):
    model_config = ConfigDict(
        strict=True,
        extra="forbid",
        str_strip_whitespace=True,
    )

    attempt_id: str = Field(pattern=r"^[a-f0-9]{32}$")
    brief: str = Field(min_length=1, max_length=4000)
    research_id: str | None = Field(
        default=None,
        pattern=r"^research_[a-f0-9]{24}$",
    )


class GenerateResponse(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")

    attempt_id: str
    scene: SceneSpec
    revision: SceneRevision
    grounding: DirectorGrounding | None = None


def _require_registered_identity(db, current_user):
    try:
        stored = read_verified_user(
            db,
            uid=current_user.uid,
        )
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Verified user registration is required.",
        ) from error

    if (
        stored.uid != current_user.uid
        or stored.email != current_user.email
        or stored.provider != current_user.provider
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Stored user identity is inconsistent.",
        )

    return stored


def _load_director_grounding(
    db,
    *,
    project_id: str,
    research_id: str | None,
    requested_by: str,
) -> DirectorGrounding | None:
    if research_id is None:
        return None

    try:
        record = read_production_research(
            db,
            studio_project_id=project_id,
            research_id=research_id,
        )
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Production research does not exist.",
        ) from error

    if record.requested_by != requested_by:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Production research does not exist.",
        )

    return create_director_grounding(record)


def _initial_scene_revision(scene: SceneSpec) -> SceneRevision:
    return build_scene_revision(
        revision_id="revision_001",
        version=1,
        parent_revision_id=None,
        created_by="agent",
        change_note=(
            "Initial Gemini Director scene plan awaiting human review."
        ),
        scene=scene,
    )


@router.post(
    "/{project_id}/attempts",
    response_model=GenerateResponse,
    status_code=status.HTTP_201_CREATED,
)
async def submit_brief(
    project_id: ResourceId,
    request: GenerateRequest,
    current_user: CurrentUser,
    db: Database,
) -> GenerateResponse:
    registered = _require_registered_identity(db, current_user)
    grounding = _load_director_grounding(
        db,
        project_id=project_id,
        research_id=request.research_id,
        requested_by=registered.uid,
    )

    try:
        scene = await generate_scene(
            db,
            studio_project_id=project_id,
            attempt_id=request.attempt_id,
            brief=request.brief,
            reservation_micro_usd=DIRECTOR_RESERVATION_MICRO_USD,
            rate=GEMINI_35_FLASH_GLOBAL_STANDARD,
            grounding=grounding,
        )

        revision = _initial_scene_revision(scene)
        save_scene_revision(
            db,
            studio_project_id=project_id,
            source_attempt_id=request.attempt_id,
            revision=revision,
        )
    except Conflict as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "A record already exists for this attempt. "
                "Inspect it before retrying."
            ),
        ) from error
    except Exception as error:
        logger.exception(
            "Generation failed for project=%s attempt=%s",
            project_id,
            request.attempt_id,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=(
                "Generation did not complete. "
                "Keep this attempt ID for inspection."
            ),
        ) from error

    return GenerateResponse(
        attempt_id=request.attempt_id,
        scene=scene,
        revision=revision,
        grounding=grounding,
    )
