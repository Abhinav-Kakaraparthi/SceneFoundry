"""Geometry and camera placement for one shot's blocking preview."""

from typing import Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from scenefoundry.domain.objects import VisualObject
from scenefoundry.domain.spatial import CameraSpec


class ShotLayout(BaseModel):
    model_config = ConfigDict(strict=True, frozen=True, extra="forbid")

    shot_id: str = Field(pattern=r"^[a-z][a-z0-9_]{0,63}$")
    camera: CameraSpec
    objects: tuple[VisualObject, ...] = Field(
        min_length=1, max_length=100, strict=False
    )

    @model_validator(mode="after")
    def validate_object_ids(self) -> Self:
        seen: set[str] = set()
        for item in self.objects:
            if item.object_id in seen:
                raise ValueError(f"Duplicate object ID: {item.object_id}")
            seen.add(item.object_id)
        return self
