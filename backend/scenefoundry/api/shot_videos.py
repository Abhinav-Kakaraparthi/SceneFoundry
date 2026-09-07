"""Submit Veo generation from a saved source shot."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path
from google.api_core.exceptions import Conflict
from google.cloud import firestore
from pydantic import BaseModel, ConfigDict, Field

from scenefoundry.api.auth import CurrentUser
from scenefoundry.api.projects import get_db
from scenefoundry.domain.approval import require_approved_revision
from scenefoundry.domain.production_direction import (
    ProductionDirection,
    create_production_direction,
)
from scenefoundry.storage.approvals import read_revision_approval
from scenefoundry.storage.projects import read_production_project
from scenefoundry.storage.revisions import read_scene_revision
from scenefoundry.video.production import start_veo
from scenefoundry.video.shot_request import build_shot_video_request

router = APIRouter(prefix="/v1/veo/projects", tags=["video"])
StudioId = Annotated[str, Path(pattern=r"^[A-Za-z0-9_-]{1,64}$")]
AttemptId = Annotated[str, Path(pattern=r"^[0-9a-f]{32}$")]
ShotId = Annotated[str, Path(pattern=r"^[a-z][a-z0-9_]{0,63}$")]


class VideoSubmission(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")
    attempt_id: str = Field(pattern=r"^[0-9a-f]{32}$")
    revision_id: str = Field(pattern=r"^[a-z][a-z0-9_]{0,63}$")


def _load_production_direction(
    db,
    *,
    project_id: str,
    requested_by: str,
) -> ProductionDirection | None:
    if not project_id.startswith("project_"):
        return None

    try:
        project = read_production_project(
            db,
            project_id=project_id,
            created_by=requested_by,
        )
    except ValueError as error:
        raise HTTPException(
            404,
            "Production project not found.",
        ) from error

    return create_production_direction(project)


@router.post(
    "/{project_id}/attempts/{source_attempt_id}/shots/{shot_id}/videos",
    status_code=202,
)
def submit_shot_video(
    project_id: StudioId,
    source_attempt_id: AttemptId,
    shot_id: ShotId,
    request: VideoSubmission,
    current_user: CurrentUser,
    db: Annotated[firestore.Client, Depends(get_db)],
) -> dict[str, str]:
    direction = _load_production_direction(
        db,
        project_id=project_id,
        requested_by=current_user.uid,
    )

    try:
        revision = read_scene_revision(
            db,
            studio_project_id=project_id,
            source_attempt_id=source_attempt_id,
            revision_id=request.revision_id,
        )
    except ValueError as error:
        raise HTTPException(404, str(error)) from error

    approval = read_revision_approval(
        db,
        studio_project_id=project_id,
        source_attempt_id=source_attempt_id,
        revision_id=request.revision_id,
    )
    try:
        require_approved_revision(request.revision_id, approval)
    except ValueError as error:
        raise HTTPException(409, str(error)) from error
    try:
        prepared = build_shot_video_request(
            revision.scene,
            shot_id,
            direction=direction,
        )
    except ValueError as error:
        raise HTTPException(422, str(error)) from error

    try:
        start_veo(
            db,
            studio_project_id=project_id,
            attempt_id=request.attempt_id,
            prompt=prepared.prompt,
            duration_seconds=prepared.duration_seconds,
            aspect_ratio=prepared.aspect_ratio,
            source_attempt_id=source_attempt_id,
            source_revision_id=request.revision_id,
            source_shot_id=prepared.shot_id,
            prompt_version=prepared.prompt_version,
        )
    except Conflict as error:
        raise HTTPException(409, "Video attempt already exists; check its status.") from error
    except RuntimeError as error:
        raise HTTPException(
            503, "Submission needs inspection. Keep the attempt ID; do not resubmit."
        ) from error

    return {"attempt_id": request.attempt_id, "status": "submitted"}
