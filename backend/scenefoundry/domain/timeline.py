from typing import Self

from pydantic import BaseModel, ConfigDict, Field, model_validator


class FrameRange(BaseModel):
    """A nonempty frame interval: start inclusive, end exclusive."""

    model_config = ConfigDict(strict=True, frozen=True, extra="forbid")

    start: int = Field(ge=0)
    end: int = Field(gt=0)

    @model_validator(mode="after")
    def validate_order(self) -> Self:
        if self.end <= self.start:
            raise ValueError("end must be greater than start")
        return self

    @property
    def frame_count(self) -> int:
        return self.end - self.start