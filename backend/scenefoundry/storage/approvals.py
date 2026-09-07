from google.api_core.exceptions import AlreadyExists
from google.cloud import firestore

from scenefoundry.domain.approval import RevisionApproval
from scenefoundry.storage.revisions import read_scene_revision


def _approval_document(
    db,
    *,
    studio_project_id: str,
    source_attempt_id: str,
    revision_id: str,
):
    return db.document(
        "projects",
        studio_project_id,
        "attempts",
        source_attempt_id,
        "revision_approvals",
        revision_id,
    )


def _approval_collection(
    db,
    *,
    studio_project_id: str,
    source_attempt_id: str,
):
    return db.collection(
        "projects",
        studio_project_id,
        "attempts",
        source_attempt_id,
        "revision_approvals",
    )


def _parse_approval(snapshot) -> RevisionApproval:
    payload = snapshot.to_dict()
    payload.pop("created_at", None)

    approval = RevisionApproval.model_validate(payload)
    if approval.revision_id != snapshot.id:
        raise ValueError("Approval document identity is inconsistent.")
    return approval


def _same_approval(
    snapshot,
    expected: RevisionApproval,
) -> bool:
    try:
        return _parse_approval(snapshot) == expected
    except (TypeError, ValueError):
        return False


def read_revision_approval(
    db,
    *,
    studio_project_id: str,
    source_attempt_id: str,
    revision_id: str,
) -> RevisionApproval | None:
    snapshot = _approval_document(
        db,
        studio_project_id=studio_project_id,
        source_attempt_id=source_attempt_id,
        revision_id=revision_id,
    ).get(timeout=15)

    if not snapshot.exists:
        return None

    return _parse_approval(snapshot)


def save_revision_approval(
    db,
    *,
    studio_project_id: str,
    source_attempt_id: str,
    approval: RevisionApproval,
) -> bool:
    """Create the first decision or accept an identical retry."""

    read_scene_revision(
        db,
        studio_project_id=studio_project_id,
        source_attempt_id=source_attempt_id,
        revision_id=approval.revision_id,
    )

    document = _approval_document(
        db,
        studio_project_id=studio_project_id,
        source_attempt_id=source_attempt_id,
        revision_id=approval.revision_id,
    )
    existing = document.get(timeout=15)

    if existing.exists:
        if _same_approval(existing, approval):
            return False
        raise ValueError(
            "Scene revision already has a different decision."
        )

    payload = approval.model_dump(mode="json")
    payload["created_at"] = firestore.SERVER_TIMESTAMP

    try:
        document.create(payload)
    except AlreadyExists:
        existing = document.get(timeout=15)
        if existing.exists and _same_approval(existing, approval):
            return False
        raise ValueError(
            "Scene revision was concurrently reviewed differently."
        )

    return True


def list_revision_approvals(
    db,
    *,
    studio_project_id: str,
    source_attempt_id: str,
) -> tuple[RevisionApproval, ...]:
    approvals = (
        _parse_approval(snapshot)
        for snapshot in _approval_collection(
            db,
            studio_project_id=studio_project_id,
            source_attempt_id=source_attempt_id,
        ).stream(timeout=15)
    )
    return tuple(
        sorted(
            approvals,
            key=lambda approval: approval.revision_id,
        )
    )
