"""Immutable metadata linking a preview revision to its source shot."""

import re

from google.api_core.exceptions import Conflict
from google.cloud import firestore
from pydantic import BaseModel, ConfigDict, Field


class PreviewRecord(BaseModel):
    model_config = ConfigDict(strict=True, frozen=True, extra="forbid")

    source_attempt_id: str = Field(pattern=r"^[a-f0-9]{32}$")
    layout_attempt_id: str = Field(pattern=r"^[a-f0-9]{32}$")
    revision_id: str = Field(pattern=r"^[a-f0-9]{32}$")
    shot_id: str = Field(pattern=r"^[a-z][a-z0-9_]{0,63}$")
    caption: str = Field(min_length=1, max_length=240)
    image_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    layout_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")


def save_preview(
    db: firestore.Client,
    *,
    studio_project_id: str,
    preview: PreviewRecord,
) -> bool:
    """Create metadata once; reject conflicting reuse of a revision ID."""
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", studio_project_id):
        raise ValueError("Invalid studio project ID.")

    reference = db.document(
        "projects", studio_project_id,
        "attempts", preview.source_attempt_id,
        "previews", preview.revision_id,
    )
    payload = preview.model_dump(mode="json")
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
            raise ValueError("Preview revision already has different metadata.")
        return False
    return True
