"""Spatial contracts: meters, right-handed coordinates, Z pointing up."""

from typing import Self

from pydantic import BaseModel, ConfigDict, Field, model_validator


class Vector3(BaseModel):
    model_config = ConfigDict(
        strict=True, frozen=True, extra="forbid", allow_inf_nan=False
    )

    x: float
    y: float
    z: float

    def as_tuple(self) -> tuple[float, float, float]:
        return self.x, self.y, self.z


class CameraSpec(BaseModel):
    """Perspective camera with a fixed 36 mm horizontal sensor width."""

    model_config = ConfigDict(
        strict=True, frozen=True, extra="forbid", allow_inf_nan=False
    )

    position: Vector3
    target: Vector3
    focal_length_mm: float = Field(default=50.0, ge=10.0, le=200.0)

    @model_validator(mode="after")
    def validate_direction(self) -> Self:
        distance_squared = sum(
            (origin - destination) ** 2
            for origin, destination in zip(
                self.position.as_tuple(), self.target.as_tuple()
            )
        )
        if distance_squared < 0.0001 ** 2:
            raise ValueError("Camera and target must be at least 0.1 mm apart.")
        return self
