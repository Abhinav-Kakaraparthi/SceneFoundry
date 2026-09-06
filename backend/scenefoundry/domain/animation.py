"""Bind translation tracks to validated shot geometry and timing."""

from typing import Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from scenefoundry.domain.layout import ShotLayout
from scenefoundry.domain.motion import TranslationTrack
from scenefoundry.domain.shot import ShotSpec


class AnimatedShot(BaseModel):
    model_config = ConfigDict(strict=True, frozen=True, extra="forbid")

    shot: ShotSpec
    layout: ShotLayout
    tracks: tuple[TranslationTrack, ...] = Field(
        min_length=1, max_length=100, strict=False
    )

    @model_validator(mode="after")
    def validate_bindings(self) -> Self:
        if self.layout.shot_id != self.shot.shot_id:
            raise ValueError("Layout and source shot IDs must match.")

        last_frame = self.shot.frames.frame_count - 1
        available = {item.object_id for item in self.layout.objects}
        assigned: set[str] = set()

        for track in self.tracks:
            if track.keyframes[-1].frame != last_frame:
                raise ValueError(
                    f"Each track must end at local frame {last_frame}."
                )
            for object_id in track.object_ids:
                if object_id not in available:
                    raise ValueError(f"Unknown animated object: {object_id}")
                if object_id in assigned:
                    raise ValueError(
                        f"Object belongs to multiple tracks: {object_id}"
                    )
                assigned.add(object_id)
        return self
