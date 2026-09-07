from typing import Literal

from fastapi import APIRouter, HTTPException, Response, status
from pydantic import BaseModel, ConfigDict, Field

from scenefoundry.api.projects import Database, ResourceId
from scenefoundry.domain.artifacts import ArtifactKind
from scenefoundry.domain.revision import SceneRevision
from scenefoundry.domain.revision_workflow import prepare_scene_revision
from scenefoundry.domain.scene import SceneSpec
from scenefoundry.storage.revisions import (
    save_scene_revision as store_scene_revision,
)
from scenefoundry.storage.revisions import read_scene_revision


router = APIRouter(
    prefix="/v1/projects/{project_id}/attempts/{attempt_id}/revisions",
    tags=["scene-revisions"],
)


class CreateRevisionRequest(BaseModel):
    """Editable input accepted when creating a child scene revision."""

    model_config = ConfigDict(strict=True, extra="forbid")

    revision_id: str = Field(pattern=r"^[a-z][a-z0-9_]{0,63}$")
    parent_revision_id: str = Field(pattern=r"^[a-z][a-z0-9_]{0,63}$")
    created_by: Literal["director", "agent"] = "director"
    change_note: str = Field(min_length=1, max_length=500)
    scene: SceneSpec


class CreateRevisionResponse(BaseModel):
    """Stored child revision plus its authoritative regeneration impact."""

    model_config = ConfigDict(strict=True, extra="forbid")

    created: bool
    revision: SceneRevision
    invalidated_artifacts: tuple[ArtifactKind, ...]


@router.post(
    "",
    response_model=CreateRevisionResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_revision(
    project_id: ResourceId,
    attempt_id: ResourceId,
    request: CreateRevisionRequest,
    response: Response,
    db: Database,
) -> CreateRevisionResponse:
    try:
        parent = read_scene_revision(
            db=db,
            studio_project_id=project_id,
            source_attempt_id=attempt_id,
            revision_id=request.parent_revision_id,
        )
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(error),
        ) from error

    if parent is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Parent scene revision does not exist.",
        )

    try:
        prepared = prepare_scene_revision(
            parent=parent,
            revision_id=request.revision_id,
            created_by=request.created_by,
            change_note=request.change_note,
            scene=request.scene,
        )
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(error),
        ) from error

    try:
        created = store_scene_revision(
            db=db,
            studio_project_id=project_id,
            source_attempt_id=attempt_id,
            revision=prepared.revision,
        )
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(error),
        ) from error

    if not created:
        response.status_code = status.HTTP_200_OK

    return CreateRevisionResponse(
        created=created,
        revision=prepared.revision,
        invalidated_artifacts=prepared.invalidated_artifacts,
    )
