"""Shot-local translation tracks for groups of preview objects."""

from typing import Annotated, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from scenefoundry.domain.spatial import Vector3

ObjectId = Annotated[str, Field(pattern=r"^[a-z][a-z0-9_]{0,63}$")]


class TranslationKeyframe(BaseModel):
    model_config = ConfigDict(strict=True, frozen=True, extra="forbid")

    frame: int = Field(ge=0)
    offset: Vector3


class TranslationTrack(BaseModel):
    """Apply the same world-space translation to every listed object.

    Offsets are relative to the saved layout, not the previous keyframe.
    The renderer linearly interpolates between consecutive keyframes.
    """

    model_config = ConfigDict(strict=True, frozen=True, extra="forbid")

    object_ids: tuple[ObjectId, ...] = Field(
        min_length=1, max_length=100, strict=False
    )
    keyframes: tuple[TranslationKeyframe, ...] = Field(
        min_length=2, max_length=100, strict=False
    )

    @model_validator(mode="after")
    def validate_track(self) -> Self:
        if len(set(self.object_ids)) != len(self.object_ids):
            raise ValueError("A motion track cannot contain duplicate object IDs.")
        if self.keyframes[0].frame != 0:
            raise ValueError("A motion track must begin at local frame 0.")
        for previous, current in zip(self.keyframes, self.keyframes[1:]):
            if current.frame <= previous.frame:
                raise ValueError("Keyframe numbers must be strictly increasing.")
        return self
