"""Immutable screenplay content and version contracts."""

import hashlib
from typing import Literal, Self

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)

ScreenplayFormat = Literal["fountain", "plain_text"]
ScreenplaySource = Literal["imported", "generated", "edited"]

MAX_SCREENPLAY_CHARACTERS = 500_000


def normalize_screenplay(content: str) -> str:
    """Canonicalize line endings and irrelevant trailing whitespace."""

    if not isinstance(content, str):
        raise TypeError("Screenplay content must be text.")

    normalized = content.replace("\r\n", "\n").replace("\r", "\n")
    normalized = "\n".join(
        line.rstrip()
        for line in normalized.split("\n")
    ).strip("\n")

    if not normalized.strip():
        raise ValueError("Screenplay content cannot be blank.")
    if len(normalized) > MAX_SCREENPLAY_CHARACTERS:
        raise ValueError(
            "Screenplay exceeds the supported character limit."
        )

    return normalized


def screenplay_sha256(content: str) -> str:
    """Return a stable digest for canonical screenplay text."""

    canonical = normalize_screenplay(content)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def screenplay_version_id(
    screenplay_id: str,
    version: int,
) -> str:
    """Return the canonical identifier for one numbered version."""

    if not isinstance(screenplay_id, str):
        raise TypeError("Screenplay ID must be text.")
    if not isinstance(version, int) or isinstance(version, bool):
        raise TypeError("Screenplay version must be an integer.")
    if version < 1:
        raise ValueError("Screenplay version must be positive.")

    version_id = f"{screenplay_id}_v{version:03d}"
    if len(version_id) > 64:
        raise ValueError("Screenplay version ID exceeds 64 characters.")
    return version_id


class Screenplay(BaseModel):
    """Canonical screenplay content independent of storage or generation."""

    model_config = ConfigDict(
        strict=True,
        frozen=True,
        extra="forbid",
        str_strip_whitespace=True,
    )

    title: str = Field(min_length=1, max_length=200)
    format: ScreenplayFormat
    content: str = Field(
        min_length=1,
        max_length=MAX_SCREENPLAY_CHARACTERS,
    )

    @field_validator("content", mode="before")
    @classmethod
    def canonicalize_content(cls, value):
        return normalize_screenplay(value)

    @property
    def sha256(self) -> str:
        return screenplay_sha256(self.content)


class ScreenplayVersion(BaseModel):
    """One immutable, auditable version of a screenplay."""

    model_config = ConfigDict(
        strict=True,
        frozen=True,
        extra="forbid",
        str_strip_whitespace=True,
    )

    screenplay_id: str = Field(
        pattern=r"^[a-z][a-z0-9_]{0,63}$"
    )
    version_id: str = Field(
        pattern=r"^[a-z][a-z0-9_]{0,63}$"
    )
    version: int = Field(ge=1)
    parent_version_id: str | None = Field(
        default=None,
        pattern=r"^[a-z][a-z0-9_]{0,63}$",
    )
    source: ScreenplaySource
    screenplay: Screenplay
    content_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    created_by: str = Field(
        min_length=1,
        max_length=200,
        pattern=r"^\S+$",
    )
    change_note: str | None = Field(default=None, max_length=2000)

    @model_validator(mode="after")
    def validate_lineage(self) -> Self:
        if self.content_sha256 != self.screenplay.sha256:
            raise ValueError(
                "Screenplay fingerprint does not match its content."
            )

        if self.version == 1:
            if self.parent_version_id is not None:
                raise ValueError(
                    "The initial screenplay version cannot have a parent."
                )
            if self.source == "edited":
                raise ValueError(
                    "The initial screenplay must be imported or generated."
                )
        else:
            if self.parent_version_id is None:
                raise ValueError(
                    "Later screenplay versions require a parent."
                )
            if self.parent_version_id == self.version_id:
                raise ValueError(
                    "A screenplay version cannot be its own parent."
                )
            if not self.change_note:
                raise ValueError(
                    "Later screenplay versions require a change note."
                )

        return self
