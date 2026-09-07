"""Authenticated human decisions for immutable scene revisions."""

from fastapi import APIRouter, HTTPException, Response, status
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    ValidationError,
)

from scenefoundry.api.auth import RegisteredUser
from scenefoundry.api.projects import Database, ResourceId
from scenefoundry.domain.approval import (
    ApprovalDecision,
    RevisionApproval,
)
from scenefoundry.storage.approvals import save_revision_approval
from scenefoundry.storage.revisions import read_scene_revision


router = APIRouter(
    prefix=(
        "/v1/projects/{project_id}/attempts/"
        "{attempt_id}/revisions"
    ),
    tags=["scene-approvals"],
)


class ReviewRevisionRequest(BaseModel):
    """Only the human decision and optional note are client-editable."""

    model_config = ConfigDict(
        strict=True,
        extra="forbid",
        str_strip_whitespace=True,
    )

    decision: ApprovalDecision
    note: str | None = Field(default=None, max_length=2000)


class ReviewRevisionResponse(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")

    created: bool
    approval: RevisionApproval


@router.post(
    "/{revision_id}/approval",
    response_model=ReviewRevisionResponse,
    status_code=status.HTTP_201_CREATED,
)
def review_revision(
    project_id: ResourceId,
    attempt_id: ResourceId,
    revision_id: ResourceId,
    request: ReviewRevisionRequest,
    response: Response,
    current_user: RegisteredUser,
    db: Database,
) -> ReviewRevisionResponse:
    """Record one immutable decision from the signed-in director."""

    try:
        read_scene_revision(
            db,
            studio_project_id=project_id,
            source_attempt_id=attempt_id,
            revision_id=revision_id,
        )
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Scene revision does not exist.",
        ) from error

    try:
        approval = RevisionApproval(
            revision_id=revision_id,
            decision=request.decision,
            reviewer_id=current_user.uid,
            note=request.note,
        )
    except (TypeError, ValueError, ValidationError) as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="The director decision is invalid.",
        ) from error

    try:
        created = save_revision_approval(
            db,
            studio_project_id=project_id,
            source_attempt_id=attempt_id,
            approval=approval,
        )
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(error),
        ) from error

    if not created:
        response.status_code = status.HTTP_200_OK

    return ReviewRevisionResponse(
        created=created,
        approval=approval,
    )
