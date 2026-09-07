from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from scenefoundry.domain.artifacts import ArtifactKind
from scenefoundry.domain.revision import (
    SceneRevision,
    build_scene_revision,
)
from scenefoundry.domain.scene import SceneSpec
from scenefoundry.domain.scene_diff import plan_scene_revision


class PreparedSceneRevision(BaseModel):
    """An immutable child revision and its server-derived artifact impact."""

    model_config = ConfigDict(strict=True, frozen=True, extra="forbid")

    revision: SceneRevision
    invalidated_artifacts: tuple[ArtifactKind, ...] = Field(min_length=1)


def prepare_scene_revision(
    *,
    parent: SceneRevision,
    revision_id: str,
    created_by: Literal["director", "agent"],
    change_note: str,
    scene: SceneSpec,
) -> PreparedSceneRevision:
    """Build a child revision without trusting client lineage metadata."""

    plan = plan_scene_revision(parent.scene, scene)
    revision = build_scene_revision(
        revision_id=revision_id,
        version=parent.version + 1,
        parent_revision_id=parent.revision_id,
        created_by=created_by,
        change_note=change_note,
        changed_paths=plan.changed_paths,
        scene=scene,
    )

    return PreparedSceneRevision(
        revision=revision,
        invalidated_artifacts=plan.invalidated_artifacts,
    )
