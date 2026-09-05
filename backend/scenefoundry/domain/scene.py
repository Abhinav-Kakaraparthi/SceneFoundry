from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from scenefoundry.domain.shot import ShotSpec


class SceneSpec(BaseModel):
    """An ordered sequence of shots on a shared output timeline."""

    model_config = ConfigDict(strict=True, frozen=True, extra="forbid")

    scene_id: str = Field(pattern=r"^[a-z][a-z0-9_]{0,63}$")
    fps: Literal[24, 30]
    shots: tuple[ShotSpec, ...] = Field(min_length=1, strict=False)

    @model_validator(mode="after")
    def validate_timeline(self) -> Self:
        seen: set[str] = set()
        expected_start = 0

        for shot in self.shots:
            if shot.shot_id in seen:
                raise ValueError(f"Duplicate shot ID: {shot.shot_id}")
            if shot.frames.start != expected_start:
                raise ValueError(
                    f"{shot.shot_id} must start at frame {expected_start}"
                )
            seen.add(shot.shot_id)
            expected_start = shot.frames.end

        return self

    @property
    def frame_count(self) -> int:
        return self.shots[-1].frames.end