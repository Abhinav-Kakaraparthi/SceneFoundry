"""Attach immutable SceneSpec lineage to verified cinematic clips."""

from scenefoundry.domain.approval import require_approved_revision
from scenefoundry.domain.artifacts import ArtifactInput, ArtifactStamp
from scenefoundry.storage.approvals import read_revision_approval
from scenefoundry.storage.artifacts import (
    list_artifact_stamps,
    save_artifact_stamp,
)
from scenefoundry.storage.revisions import read_scene_revision


def save_cinematic_clip_provenance(
    db,
    *,
    studio_project_id: str,
    source_attempt_id: str,
    source_revision_id: str,
    shot_id: str,
    video_attempt_id: str,
    video_sha256: str,
    bucket_name: str,
    object_name: str,
    generation: int,
) -> bool:
    """Register one verified Veo clip against its approved shot plan."""

    revision = read_scene_revision(
        db,
        studio_project_id=studio_project_id,
        source_attempt_id=source_attempt_id,
        revision_id=source_revision_id,
    )
    approval = read_revision_approval(
        db,
        studio_project_id=studio_project_id,
        source_attempt_id=source_attempt_id,
        revision_id=source_revision_id,
    )
    require_approved_revision(source_revision_id, approval)

    roots = tuple(
        stamp
        for stamp in list_artifact_stamps(
            db,
            studio_project_id=studio_project_id,
            source_attempt_id=source_attempt_id,
            revision_id=source_revision_id,
            scope_id=revision.scene.scene_id,
        )
        if stamp.kind == "shot_plan"
    )
    if not roots:
        shot_plan = ArtifactStamp(
            artifact_id=f"shot_plan_{revision.scene_sha256[:24]}",
            kind="shot_plan",
            revision_id=source_revision_id,
            scope_id=revision.scene.scene_id,
            sha256=revision.scene_sha256,
        )
        save_artifact_stamp(
            db,
            studio_project_id=studio_project_id,
            source_attempt_id=source_attempt_id,
            stamp=shot_plan,
        )
        roots = (shot_plan,)

    if len(roots) != 1:
        raise ValueError(
            "Approved revision must have exactly one shot-plan artifact."
        )

    shot_plan = roots[0]
    stamp = ArtifactStamp(
        artifact_id=f"cinematic_{video_attempt_id}",
        kind="cinematic_clip",
        revision_id=source_revision_id,
        scope_id=shot_id,
        sha256=video_sha256,
        inputs=(
            ArtifactInput(
                artifact_id=shot_plan.artifact_id,
                kind=shot_plan.kind,
                sha256=shot_plan.sha256,
            ),
        ),
        uri=(
            f"gs://{bucket_name}/{object_name}"
            f"?generation={generation}"
        ),
    )
    return save_artifact_stamp(
        db,
        studio_project_id=studio_project_id,
        source_attempt_id=source_attempt_id,
        stamp=stamp,
    )
