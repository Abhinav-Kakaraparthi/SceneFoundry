from pydantic import BaseModel, ConfigDict, Field

from scenefoundry.domain.artifacts import (
    ARTIFACT_ORDER,
    ArtifactKind,
    impacted_artifacts,
)
from scenefoundry.domain.scene import SceneSpec


class SceneRevisionPlan(BaseModel):
    """Server-derived changes and artifacts invalidated by a scene revision."""

    model_config = ConfigDict(strict=True, frozen=True, extra="forbid")

    changed_paths: tuple[str, ...] = Field(min_length=1)
    invalidated_artifacts: tuple[ArtifactKind, ...] = Field(min_length=1)


def diff_scene_specs(
    parent: SceneSpec,
    candidate: SceneSpec,
) -> tuple[str, ...]:
    """Return a deterministic semantic diff between two SceneSpec values."""

    if candidate.scene_id != parent.scene_id:
        raise ValueError("A revision cannot change the scene ID.")

    changes: set[str] = set()

    if candidate.fps != parent.fps:
        changes.add("fps")

    parent_ids = tuple(shot.shot_id for shot in parent.shots)
    candidate_ids = tuple(shot.shot_id for shot in candidate.shots)

    if parent_ids != candidate_ids:
        changes.add("shots.order")

    parent_shots = {shot.shot_id: shot for shot in parent.shots}
    candidate_shots = {shot.shot_id: shot for shot in candidate.shots}

    for shot_id in parent_ids:
        if shot_id not in candidate_shots:
            changes.add(f"shots.{shot_id}.removed")
            continue

        previous = parent_shots[shot_id]
        current = candidate_shots[shot_id]

        if current.action != previous.action:
            changes.add(f"shots.{shot_id}.action")
        if current.frames != previous.frames:
            changes.add(f"shots.{shot_id}.frames")

    for shot_id in candidate_ids:
        if shot_id not in parent_shots:
            changes.add(f"shots.{shot_id}.added")

    return tuple(sorted(changes))


def plan_scene_revision(
    parent: SceneSpec,
    candidate: SceneSpec,
) -> SceneRevisionPlan:
    """Compute authoritative changes and their transitive artifact impact."""

    changed_paths = diff_scene_specs(parent, candidate)
    if not changed_paths:
        raise ValueError("A revision must change the scene.")

    affected = set(
        impacted_artifacts({"shot_plan"})
    )
    ordered_impact = tuple(
        artifact
        for artifact in ARTIFACT_ORDER
        if artifact in affected
    )

    return SceneRevisionPlan(
        changed_paths=changed_paths,
        invalidated_artifacts=ordered_impact,
    )
