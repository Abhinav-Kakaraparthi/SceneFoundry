"""Authenticated creation of immutable child scene revisions."""

from fastapi import APIRouter, HTTPException, Response, status
from pydantic import BaseModel, ConfigDict, Field

from scenefoundry.api.auth import RegisteredUser
from scenefoundry.api.projects import Database, ResourceId
from scenefoundry.domain.artifacts import ArtifactKind
from scenefoundry.domain.revision import SceneRevision
from scenefoundry.domain.revision_workflow import prepare_scene_revision
from scenefoundry.domain.scene import SceneSpec
from scenefoundry.storage.approvals import read_revision_approval
from scenefoundry.storage.revisions import (
    list_scene_revisions,
    read_scene_revision,
    save_scene_revision,
)


router = APIRouter(
    prefix="/v1/projects/{project_id}/attempts/{attempt_id}/revisions",
    tags=["scene-revisions"],
)


class CreateRevisionRequest(BaseModel):
    """Only editable scene content and its reviewed parent are accepted."""

    model_config = ConfigDict(
        strict=True,
        extra="forbid",
        str_strip_whitespace=True,
    )

    parent_revision_id: str = Field(
        pattern=r"^[a-z][a-z0-9_]{0,63}$",
    )
    change_note: str = Field(min_length=1, max_length=2000)
    scene: SceneSpec


class CreateRevisionResponse(BaseModel):
    """Stored child revision and server-derived regeneration impact."""

    model_config = ConfigDict(strict=True, extra="forbid")

    created: bool
    revision: SceneRevision
    invalidated_artifacts: tuple[ArtifactKind, ...]


def _child_revision_id(parent: SceneRevision) -> str:
    """Derive sequential lineage without trusting the browser."""

    return f"revision_{parent.version + 1:03d}"


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
    current_user: RegisteredUser,
    db: Database,
) -> CreateRevisionResponse:
    """Create one correction for a revision reviewed by this director."""

    try:
        parent = read_scene_revision(
            db,
            studio_project_id=project_id,
            source_attempt_id=attempt_id,
            revision_id=request.parent_revision_id,
        )
        approval = read_revision_approval(
            db,
            studio_project_id=project_id,
            source_attempt_id=attempt_id,
            revision_id=request.parent_revision_id,
        )
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Parent scene revision does not exist.",
        ) from error

    if approval is None or approval.decision != "changes_requested":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="The parent revision has no active change request.",
        )

    if approval.reviewer_id != current_user.uid:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the reviewing director may address this request.",
        )

    try:
        prepared = prepare_scene_revision(
            parent=parent,
            revision_id=_child_revision_id(parent),
            created_by="director",
            change_note=request.change_note,
            scene=request.scene,
        )
        history = list_scene_revisions(
            db,
            studio_project_id=project_id,
            source_attempt_id=attempt_id,
        )
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(error),
        ) from error

    if not history:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Revision history is incomplete.",
        )

    latest = history[-1]
    if (
        latest.revision_id != parent.revision_id
        and latest != prepared.revision
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A newer revision already exists.",
        )

    try:
        created = save_scene_revision(
            db,
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
