from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from scenefoundry.api.projects import Database, ResourceId
from scenefoundry.domain.revision import (
    SceneRevision,
    build_scene_revision,
)
from scenefoundry.domain.scene import SceneSpec
from scenefoundry.storage.revisions import (
    list_scene_revisions,
    read_scene_revision,
    save_scene_revision,
)

router = APIRouter(
    prefix="/v1/projects/{project_id}/attempts/{attempt_id}/revisions",
    tags=["scene-revisions"],
)


class BootstrapRevisionRequest(BaseModel):
    model_config = ConfigDict(
        strict=True,
        extra="forbid",
        str_strip_whitespace=True,
    )

    revision_id: str = Field(
        default="revision_001",
        pattern=r"^[a-z][a-z0-9_]{0,63}$",
    )
    change_note: str = Field(
        default="Initial approved scene plan.",
        min_length=1,
        max_length=2000,
    )


class RevisionWriteResult(BaseModel):
    created: bool
    revision: SceneRevision


def _source_scene(
    db,
    *,
    project_id: str,
    attempt_id: str,
) -> SceneSpec:
    attempt = db.document(
        "projects",
        project_id,
        "attempts",
        attempt_id,
    )
    snapshot = attempt.get(timeout=15)

    if not snapshot.exists:
        raise HTTPException(status_code=404, detail="Attempt not found.")
    if snapshot.get("status") != "succeeded":
        raise HTTPException(status_code=409, detail="Scene is not ready.")

    response = attempt.collection(
        "responses"
    ).document("final").get(timeout=15)

    if not response.exists:
        raise HTTPException(
            status_code=409,
            detail="Saved scene response is unavailable.",
        )

    text = response.get("text")
    if not isinstance(text, str):
        raise HTTPException(
            status_code=409,
            detail="Saved scene response is invalid.",
        )

    return SceneSpec.model_validate_json(text)


@router.post(
    "/bootstrap",
    response_model=RevisionWriteResult,
)
def bootstrap_revision(
    body: BootstrapRevisionRequest,
    project_id: ResourceId,
    attempt_id: ResourceId,
    db: Database,
) -> RevisionWriteResult:
    scene = _source_scene(
        db,
        project_id=project_id,
        attempt_id=attempt_id,
    )
    revision = build_scene_revision(
        revision_id=body.revision_id,
        version=1,
        parent_revision_id=None,
        created_by="director",
        change_note=body.change_note,
        scene=scene,
    )

    try:
        created = save_scene_revision(
            db,
            studio_project_id=project_id,
            source_attempt_id=attempt_id,
            revision=revision,
        )
    except ValueError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error

    return RevisionWriteResult(
        created=created,
        revision=revision,
    )


@router.get("", response_model=list[SceneRevision])
def revisions(
    project_id: ResourceId,
    attempt_id: ResourceId,
    db: Database,
) -> list[SceneRevision]:
    attempt = db.document(
        "projects",
        project_id,
        "attempts",
        attempt_id,
    ).get(timeout=15)

    if not attempt.exists:
        raise HTTPException(status_code=404, detail="Attempt not found.")

    return list(
        list_scene_revisions(
            db,
            studio_project_id=project_id,
            source_attempt_id=attempt_id,
        )
    )


@router.get("/{revision_id}", response_model=SceneRevision)
def revision(
    project_id: ResourceId,
    attempt_id: ResourceId,
    revision_id: ResourceId,
    db: Database,
) -> SceneRevision:
    try:
        return read_scene_revision(
            db,
            studio_project_id=project_id,
            source_attempt_id=attempt_id,
            revision_id=revision_id,
        )
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
