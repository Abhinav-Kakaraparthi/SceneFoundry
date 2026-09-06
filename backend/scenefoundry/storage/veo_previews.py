"""Discoverable links between source shots and generated Veo clips."""

from typing import Annotated, Literal

from google.api_core.exceptions import Conflict
from google.cloud import firestore
from pydantic import BaseModel, ConfigDict, Field

AttemptId = Annotated[str, Field(pattern=r"^[0-9a-f]{32}$")]


class CloudVideo(BaseModel):
    model_config = ConfigDict(strict=True, frozen=True, extra="forbid")

    bucket_name: str = Field(
        pattern=r"^[a-z0-9][a-z0-9._-]{1,61}[a-z0-9]$"
    )
    object_name: str = Field(
        pattern=(
            r"^projects/[A-Za-z0-9_-]{1,64}/videos/"
            r"[0-9a-f]{32}/preview\.mp4$"
        )
    )
    generation: int = Field(gt=0)
    size_bytes: int = Field(gt=0)


class VeoPreview(BaseModel):
    model_config = ConfigDict(strict=True, frozen=True, extra="forbid")

    source_attempt_id: AttemptId
    video_attempt_id: AttemptId
    shot_id: str = Field(pattern=r"^[a-z][a-z0-9_]{0,63}$")
    model: Literal["veo-3.1-fast-generate-001"]
    fps: Literal[24]
    frame_count: int = Field(gt=0)
    video_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    cloud_video: CloudVideo | None = None
    caption: str = Field(min_length=1, max_length=240)


def save_veo_preview(
    db: firestore.Client,
    *,
    studio_project_id: str,
    preview: VeoPreview,
) -> bool:
    """Create an immutable link; accept an identical registration."""
    if not studio_project_id or "/" in studio_project_id:
        raise ValueError("Invalid studio project ID.")

    reference = db.document(
        "projects", studio_project_id,
        "attempts", preview.source_attempt_id,
        "veo_previews", preview.video_attempt_id,
    )
    payload = preview.model_dump(mode="json")
    try:
        reference.create(
            payload | {"created_at": firestore.SERVER_TIMESTAMP},
            timeout=15,
        )
        return True
    except Conflict:
        existing = reference.get(timeout=15).to_dict()
        if existing and all(existing.get(key) == value for key, value in payload.items()):
            return False
        raise ValueError("A different Veo preview is already registered.") from None
