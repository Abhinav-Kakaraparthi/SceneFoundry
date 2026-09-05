from pydantic import BaseModel, ConfigDict, Field

from scenefoundry.domain.timeline import FrameRange


class ShotSpec(BaseModel):
    """A shot's identity, visible action, and position on the scene timeline."""

    model_config = ConfigDict(
        strict=True,
        frozen=True,
        extra="forbid",
        str_strip_whitespace=True,
    )

    shot_id: str = Field(pattern=r"^[a-z][a-z0-9_]{0,63}$")
    action: str = Field(min_length=1, max_length=2000)
    frames: FrameRange