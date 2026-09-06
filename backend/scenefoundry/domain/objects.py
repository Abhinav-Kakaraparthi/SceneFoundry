"""Reusable primitive objects for scene blocking previews."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from scenefoundry.domain.spatial import Vector3


class Dimensions(BaseModel):
    """Full local-axis extents in meters, before rotation."""

    model_config = ConfigDict(
        strict=True, frozen=True, extra="forbid", allow_inf_nan=False
    )

    x: float = Field(gt=0, le=100)
    y: float = Field(gt=0, le=100)
    z: float = Field(gt=0, le=100)


class MaterialSpec(BaseModel):
    model_config = ConfigDict(
        strict=True, frozen=True, extra="forbid", allow_inf_nan=False
    )

    @field_validator("color_hex", mode="before")
    @classmethod
    def normalize_color_hex(cls, value: object) -> object:
        """Canonicalize bare RGB hex strings without guessing colors."""
        if (
            isinstance(value, str)
            and len(value) == 6
            and all(character in "0123456789abcdefABCDEF" for character in value)
        ):
            return "#" + value
        return value

    color_hex: str = Field(pattern=r"^#[0-9A-Fa-f]{6}$")
    roughness: float = Field(default=0.5, ge=0, le=1)
    metallic: float = Field(default=0.0, ge=0, le=1)


class VisualObject(BaseModel):
    """A centered primitive; cylinders use local Z as their axis."""

    model_config = ConfigDict(strict=True, frozen=True, extra="forbid")

    object_id: str = Field(pattern=r"^[a-z][a-z0-9_]{0,63}$")
    shape: Literal["box", "ellipsoid", "cylinder"]
    dimensions: Dimensions
    position: Vector3
    rotation_degrees: Vector3 = Field(
        default_factory=lambda: Vector3(x=0.0, y=0.0, z=0.0)
    )
    material: MaterialSpec
