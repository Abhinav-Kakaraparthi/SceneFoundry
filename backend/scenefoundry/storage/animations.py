"""Immutable metadata for rendered blocking animations."""

import re
from typing import Annotated, Literal

from google.api_core.exceptions import Conflict
from google.cloud import firestore
from pydantic import BaseModel, ConfigDict, Field

ResourceId = Annotated[str, Field(pattern=r"^[a-f0-9]{32}$")]


class AnimationRecord(BaseModel):
    model_config = ConfigDict(strict=True, frozen=True, extra="forbid")

    source_attempt_id: ResourceId
    layout_attempt_id: ResourceId
    layout_revision_id: ResourceId
    animation_id: ResourceId
    render_id: ResourceId
    shot_id: str = Field(pattern=r"^[a-z][a-z0-9_]{0,63}$")
    fps: Literal[24, 30]
    frame_count: int = Field(ge=1)
    video_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    caption: str = Field(min_length=1, max_length=240)


def save_animation(
    db: firestore.Client,
    *,
    studio_project_id: str,
    animation: AnimationRecord,
) -> bool:
    """Register a render once; reject conflicting metadata."""
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", studio_project_id):
        raise ValueError("Invalid studio project ID.")

    reference = db.document(
        "projects", studio_project_id,
        "attempts", animation.source_attempt_id,
        "animations", animation.render_id,
    )
    payload = animation.model_dump(mode="json")
    try:
        reference.create(
            {**payload, "created_at": firestore.SERVER_TIMESTAMP},
            timeout=15,
        )
    except Conflict:
        existing = reference.get(timeout=15).to_dict()
        if existing is None or any(
            existing.get(key) != value for key, value in payload.items()
        ):
            raise ValueError("Animation render already has different metadata.")
        return False
    return True
