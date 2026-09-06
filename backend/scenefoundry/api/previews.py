"""Read locally rendered preview images during desktop development."""

from typing import Annotated

from fastapi import APIRouter, HTTPException, Path
from fastapi.responses import FileResponse

from scenefoundry.paths import local_data_root

router = APIRouter(prefix="/v1/previews", tags=["previews"])
RenderId = Annotated[str, Path(pattern=r"^[a-f0-9]{32}$")]


@router.get("/{attempt_id}/revisions/{revision_id}/image")
def read_preview(attempt_id: RenderId, revision_id: RenderId) -> FileResponse:
    image = (
        local_data_root()
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
    video = (
        local_data_root()
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
