"""Immutable SceneFoundry production configuration."""

from datetime import datetime, timezone
from hashlib import sha256
import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


ProjectGenre = Literal[
    "action",
    "comedy",
    "documentary",
    "drama",
    "fantasy",
    "romance",
    "science_fiction",
    "thriller",
]

VisualStyle = Literal[
    "anime",
    "cinematic_realism",
    "documentary",
    "graphic_novel",
    "neo_noir",
    "retro_futurism",
    "stop_motion",
    "watercolor",
]

AspectRatio = Literal["9:16", "16:9"]
ProjectStatus = Literal["development"]


class ProductionProject(BaseModel):
    """One immutable, user-owned production configuration."""

    model_config = ConfigDict(
        strict=True,
        frozen=True,
        extra="forbid",
        str_strip_whitespace=True,
    )

    project_id: str = Field(pattern=r"^project_[a-f0-9]{24}$")
    creation_id: str = Field(pattern=r"^[a-f0-9]{32}$")
    created_by: str = Field(
        min_length=1,
        max_length=128,
        pattern=r"^[A-Za-z0-9_-]+$",
    )
    title: str = Field(min_length=1, max_length=120)
    premise: str = Field(min_length=1, max_length=4000)
    genre: ProjectGenre
    visual_style: VisualStyle
    aspect_ratio: AspectRatio
    episode_count: int = Field(ge=1, le=12)
    seconds_per_episode: int = Field(ge=4, le=120)
    budget_micro_usd: int = Field(ge=0, le=1_000_000_000)
    status: ProjectStatus = "development"
    created_at: datetime

    @field_validator("created_at")
    @classmethod
    def require_utc_timestamp(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("Project creation time must include a timezone.")
        return value.astimezone(timezone.utc)


def production_project_id(
    *,
    created_by: str,
    creation_id: str,
) -> str:
    """Derive a stable project identity from its owner and creation request."""

    if not re.fullmatch(r"[A-Za-z0-9_-]{1,128}", created_by):
        raise ValueError("Project owner identity is invalid.")
    if not re.fullmatch(r"[a-f0-9]{32}", creation_id):
        raise ValueError("Project creation identity is invalid.")

    digest = sha256(
        f"{created_by}:{creation_id}".encode("utf-8")
    ).hexdigest()
    return f"project_{digest[:24]}"


def build_production_project(
    *,
    creation_id: str,
    created_by: str,
    title: str,
    premise: str,
    genre: ProjectGenre,
    visual_style: VisualStyle,
    aspect_ratio: AspectRatio,
    episode_count: int,
    seconds_per_episode: int,
    budget_cents: int,
    created_at: datetime | None = None,
) -> ProductionProject:
    """Build the server-owned production record from validated user choices."""

    if type(budget_cents) is not int:
        raise TypeError("Project budget must be integer cents.")
    if not 0 <= budget_cents <= 100_000:
        raise ValueError("Project budget must be between $0 and $1,000.")

    return ProductionProject(
        project_id=production_project_id(
            created_by=created_by,
            creation_id=creation_id,
        ),
        creation_id=creation_id,
        created_by=created_by,
        title=title,
        premise=premise,
        genre=genre,
        visual_style=visual_style,
        aspect_ratio=aspect_ratio,
        episode_count=episode_count,
        seconds_per_episode=seconds_per_episode,
        budget_micro_usd=budget_cents * 10_000,
        created_at=created_at or datetime.now(timezone.utc),
    )
