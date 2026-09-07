from fastapi import APIRouter, HTTPException, Query

from scenefoundry.api.projects import Database, ResourceId
from scenefoundry.domain.artifacts import ArtifactStamp
from scenefoundry.storage.artifacts import (
    list_artifact_stamps,
    read_artifact_stamp,
)


router = APIRouter(
    prefix="/v1/projects/{project_id}/attempts/{attempt_id}/artifacts",
    tags=["artifact-provenance"],
)


def _require_attempt(
    db,
    *,
    project_id: str,
    attempt_id: str,
) -> None:
    snapshot = db.document(
        "projects",
        project_id,
        "attempts",
        attempt_id,
    ).get(timeout=15)

    if not snapshot.exists:
        raise HTTPException(status_code=404, detail="Attempt not found.")


@router.get("", response_model=list[ArtifactStamp])
def artifacts(
    project_id: ResourceId,
    attempt_id: ResourceId,
    db: Database,
    revision_id: str | None = Query(
        default=None,
        pattern=r"^[a-z][a-z0-9_]{0,63}$",
    ),
    scope_id: str | None = Query(
        default=None,
        pattern=r"^[a-z][a-z0-9_]{0,63}$",
    ),
) -> list[ArtifactStamp]:
    _require_attempt(
        db,
        project_id=project_id,
        attempt_id=attempt_id,
    )

    return list(
        list_artifact_stamps(
            db,
            studio_project_id=project_id,
            source_attempt_id=attempt_id,
            revision_id=revision_id,
            scope_id=scope_id,
        )
    )


@router.get("/{artifact_id}", response_model=ArtifactStamp)
def artifact(
    project_id: ResourceId,
    attempt_id: ResourceId,
    artifact_id: ResourceId,
    db: Database,
) -> ArtifactStamp:
    _require_attempt(
        db,
        project_id=project_id,
        attempt_id=attempt_id,
    )

    try:
        return read_artifact_stamp(
            db,
            studio_project_id=project_id,
            source_attempt_id=attempt_id,
            artifact_id=artifact_id,
        )
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
