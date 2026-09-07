import hashlib
import json
from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from scenefoundry.domain.scene import SceneSpec

Creator = Literal["director", "agent"]


def scene_sha256(scene: SceneSpec) -> str:
    """Return a stable content fingerprint independent of JSON formatting."""
    payload = json.dumps(
        scene.model_dump(mode="json"),
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


class SceneRevision(BaseModel):
    """An immutable version of the production source of truth."""

    model_config = ConfigDict(
        strict=True,
        frozen=True,
        extra="forbid",
        str_strip_whitespace=True,
    )

    revision_id: str = Field(pattern=r"^[a-z][a-z0-9_]{0,63}$")
    version: int = Field(ge=1)
    parent_revision_id: str | None = Field(
        default=None,
        pattern=r"^[a-z][a-z0-9_]{0,63}$",
    )
    created_by: Creator
    change_note: str = Field(min_length=1, max_length=2000)
    changed_paths: tuple[str, ...] = Field(default=(), strict=False)
    scene_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    scene: SceneSpec

    @field_validator("changed_paths")
    @classmethod
    def validate_changed_paths(
        cls,
        paths: tuple[str, ...],
    ) -> tuple[str, ...]:
        normalized = tuple(path.strip() for path in paths)
        if any(not path for path in normalized):
            raise ValueError("Changed paths must not be blank.")
        if len(set(normalized)) != len(normalized):
            raise ValueError("Changed paths must be unique.")
        return normalized

    @model_validator(mode="after")
    def validate_revision(self) -> Self:
        if self.version == 1 and self.parent_revision_id is not None:
            raise ValueError("The first revision cannot have a parent.")
        if self.version > 1 and self.parent_revision_id is None:
            raise ValueError("Later revisions require a parent.")
        if self.parent_revision_id == self.revision_id:
            raise ValueError("A revision cannot be its own parent.")
        if self.scene_sha256 != scene_sha256(self.scene):
            raise ValueError("Scene fingerprint does not match its content.")
        return self


def build_scene_revision(
    *,
    revision_id: str,
    version: int,
    parent_revision_id: str | None,
    created_by: Creator,
    change_note: str,
    scene: SceneSpec,
    changed_paths: tuple[str, ...] = (),
) -> SceneRevision:
    return SceneRevision(
        revision_id=revision_id,
        version=version,
        parent_revision_id=parent_revision_id,
        created_by=created_by,
        change_note=change_note,
        changed_paths=changed_paths,
        scene_sha256=scene_sha256(scene),
        scene=scene,
    )
