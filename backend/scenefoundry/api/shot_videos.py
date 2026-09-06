"""Submit Veo generation from a saved source shot."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path
from google.api_core.exceptions import Conflict
from google.cloud import firestore
from pydantic import BaseModel, ConfigDict, Field

from scenefoundry.api.projects import get_db
from scenefoundry.domain.scene import SceneSpec
from scenefoundry.video.production import start_veo
from scenefoundry.video.shot_request import build_shot_video_request

router = APIRouter(prefix="/v1/veo/projects", tags=["video"])
StudioId = Annotated[str, Path(pattern=r"^[A-Za-z0-9_-]{1,64}$")]
AttemptId = Annotated[str, Path(pattern=r"^[0-9a-f]{32}$")]
ShotId = Annotated[str, Path(pattern=r"^[a-z][a-z0-9_]{0,63}$")]


class VideoSubmission(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")
    attempt_id: str = Field(pattern=r"^[0-9a-f]{32}$")


@router.post(
    "/{project_id}/attempts/{source_attempt_id}/shots/{shot_id}/videos",
    status_code=202,
)
def submit_shot_video(
    project_id: StudioId,
    source_attempt_id: AttemptId,
    shot_id: ShotId,
    request: VideoSubmission,
    db: Annotated[firestore.Client, Depends(get_db)],
) -> dict[str, str]:
    source = db.document("projects", project_id, "attempts", source_attempt_id)
    snapshot = source.get(timeout=15)
    if not snapshot.exists:
        raise HTTPException(404, "Source attempt not found.")
    if snapshot.get("status") != "succeeded":
        raise HTTPException(409, "Source scene is not ready.")

    saved = source.collection("responses").document("final").get(timeout=15)
    if not saved.exists:
        raise HTTPException(409, "Source scene response is unavailable.")

    scene = SceneSpec.model_validate_json(saved.get("text"))
    try:
        prepared = build_shot_video_request(scene, shot_id)
    except ValueError as error:
        raise HTTPException(422, str(error)) from error

    try:
        start_veo(
            db,
            studio_project_id=project_id,
            attempt_id=request.attempt_id,
            prompt=prepared.prompt,
            duration_seconds=prepared.duration_seconds,
            source_attempt_id=source_attempt_id,
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
