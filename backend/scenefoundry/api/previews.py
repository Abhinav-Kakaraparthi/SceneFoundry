"""Read locally rendered preview images during desktop development."""

import os
from pathlib import Path as FilePath
from typing import Annotated

from fastapi import APIRouter, HTTPException, Path
from fastapi.responses import FileResponse

router = APIRouter(prefix="/v1/previews", tags=["previews"])
RenderId = Annotated[str, Path(pattern=r"^[a-f0-9]{32}$")]


@router.get("/{attempt_id}/revisions/{revision_id}/image")
def read_preview(attempt_id: RenderId, revision_id: RenderId) -> FileResponse:
    local_data = os.environ.get("LOCALAPPDATA")
    if not local_data:
        raise HTTPException(503, "Local preview storage is not configured.")

    image = (
        FilePath(local_data)
        / "SceneFoundry"
        / "renders"
        / attempt_id
        / "revisions"
        / revision_id
        / "preview.png"
    )
    if not image.is_file():
        raise HTTPException(404, "Preview image not found.")

    return FileResponse(
        image,
        media_type="image/png",
        headers={"Cache-Control": "no-store"},
    )

@router.get("/animations/{animation_id}/renders/{render_id}/video")
def read_animation(animation_id: RenderId, render_id: RenderId) -> FileResponse:
    local_data = os.environ.get("LOCALAPPDATA")
    if not local_data:
        raise HTTPException(503, "Local preview storage is not configured.")

    video = (
        FilePath(local_data)
        / "SceneFoundry"
        / "animations"
        / animation_id
        / "renders"
        / render_id
        / "preview.mp4"
    )
    if not video.is_file():
        raise HTTPException(404, "Animation video not found.")

    return FileResponse(
        video,
        media_type="video/mp4",
        headers={"Cache-Control": "no-store"},
    )
