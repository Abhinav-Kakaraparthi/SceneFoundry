from typing import Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict

from scenefoundry.api.projects import Database, ResourceId
from scenefoundry.domain.approval import RevisionApproval
from scenefoundry.domain.revision import SceneRevision
from scenefoundry.storage.approvals import list_revision_approvals
from scenefoundry.storage.revisions import list_scene_revisions


RevisionState = Literal[
    "pending",
    "approved",
    "changes_requested",
]


class RevisionStatus(BaseModel):
    """One revision joined with its immutable director decision."""

    model_config = ConfigDict(strict=True, frozen=True, extra="forbid")

    revision: SceneRevision
    state: RevisionState
    approval: RevisionApproval | None = None


router = APIRouter(
    prefix="/v1/projects/{project_id}/attempts/{attempt_id}/revisions",
    tags=["scene-revisions"],
)


@router.get("/status", response_model=list[RevisionStatus])
def revision_status(
    project_id: ResourceId,
    attempt_id: ResourceId,
    db: Database,
) -> list[RevisionStatus]:
    attempt = db.document(
        "projects",
        project_id,
        "attempts",
        attempt_id,
    ).get(timeout=15)

    if not attempt.exists:
        raise HTTPException(status_code=404, detail="Attempt not found.")

    revisions = list_scene_revisions(
        db,
        studio_project_id=project_id,
        source_attempt_id=attempt_id,
    )
    approvals = {
        approval.revision_id: approval
        for approval in list_revision_approvals(
            db,
            studio_project_id=project_id,
            source_attempt_id=attempt_id,
        )
    }

    return [
        RevisionStatus(
            revision=revision,
            approval=approvals.get(revision.revision_id),
            state=(
                approvals[revision.revision_id].decision
                if revision.revision_id in approvals
                else "pending"
            ),
        )
        for revision in revisions
    ]
