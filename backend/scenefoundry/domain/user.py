"""Verified application-user identity contracts."""

from typing import Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
)


class VerifiedUser(BaseModel):
    """A Google identity accepted by SceneFoundry."""

    model_config = ConfigDict(
        strict=True,
        frozen=True,
        extra="forbid",
        str_strip_whitespace=True,
    )

    uid: str = Field(
        min_length=1,
        max_length=128,
        pattern=r"^[A-Za-z0-9_-]+$",
    )
    email: str = Field(min_length=3, max_length=320)
    email_verified: Literal[True] = True
    name: str = Field(min_length=1, max_length=200)
    picture_url: str | None = Field(
        default=None,
        max_length=2048,
        pattern=r"^https://",
    )
    provider: Literal["google"] = "google"

    @field_validator("email", mode="before")
    @classmethod
    def normalize_email(cls, value):
        if not isinstance(value, str):
            raise TypeError("User email must be text.")

        normalized = value.strip().casefold()
        local, separator, domain = normalized.partition("@")
        if (
            not separator
            or not local
            or "." not in domain
            or domain.startswith(".")
            or domain.endswith(".")
        ):
            raise ValueError("User email is invalid.")

        return normalized
