"""Serve locally saved Veo videos by attempt ID."""

import os
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, HTTPException, Path as ApiPath
from fastapi.responses import FileResponse

router = APIRouter(prefix="/v1/veo", tags=["video"])
AttemptId = Annotated[str, ApiPath(pattern=r"^[0-9a-f]{32}$")]


@router.get("/{attempt_id}/video")
def get_veo_video(attempt_id: AttemptId) -> FileResponse:
    local_data = os.environ.get("LOCALAPPDATA")
    if not local_data:
        raise HTTPException(503, "Local video storage is unavailable.")

    video = (
        Path(local_data) / "SceneFoundry" / "veo" / attempt_id / "preview.mp4"
    )
    if not video.is_file():
        raise HTTPException(404, "Video not found.")

    return FileResponse(
        video,
        media_type="video/mp4",
        headers={"Cache-Control": "no-store"},
    )

from fastapi import Depends
from google.cloud import firestore

from scenefoundry.api.projects import get_db
from scenefoundry.storage.veo_previews import VeoPreview

StudioId = Annotated[str, ApiPath(pattern=r"^[A-Za-z0-9_-]{1,64}$")]


@router.get(
    "/projects/{project_id}/attempts/{source_attempt_id}/previews",
    response_model=list[VeoPreview],
)
def list_veo_previews(
    project_id: StudioId,
    source_attempt_id: AttemptId,
    db: Annotated[firestore.Client, Depends(get_db)],
) -> list[VeoPreview]:
    source = db.document(
        "projects", project_id, "attempts", source_attempt_id
    )
    if not source.get(timeout=15).exists:
        raise HTTPException(404, "Source attempt not found.")

    query = (
        source.collection("veo_previews")
        .order_by("created_at", direction=firestore.Query.DESCENDING)
        .limit(50)
    )
    previews = []
    for snapshot in query.stream(timeout=15):
        record = snapshot.to_dict()
        record.pop("created_at", None)
        previews.append(VeoPreview.model_validate(record))
    return previews
