import re

from google.api_core.exceptions import Conflict
from google.cloud import firestore

from scenefoundry.domain.revision import SceneRevision, scene_sha256
from scenefoundry.domain.scene import SceneSpec

_IDENTIFIER = re.compile(r"^[A-Za-z0-9_-]{1,64}$")


def _validate_identifier(value: str) -> None:
    if not _IDENTIFIER.fullmatch(value):
        raise ValueError(f"Invalid resource identifier: {value!r}")


def _parse_revision(snapshot) -> SceneRevision:
    data = snapshot.to_dict()
    if data is None:
        raise ValueError("Scene revision does not exist.")
    data.pop("created_at", None)
    return SceneRevision.model_validate(data)


def _same_revision(snapshot, expected: SceneRevision) -> bool:
    try:
        existing = _parse_revision(snapshot)
    except (TypeError, ValueError):
        return False
    return existing == expected


def _validate_parent(
    parent: SceneRevision,
    child: SceneRevision,
) -> None:
    if child.parent_revision_id != parent.revision_id:
        raise ValueError("Revision parent identity is inconsistent.")
    if child.version != parent.version + 1:
        raise ValueError("Revision version must immediately follow its parent.")
    if child.scene.scene_id != parent.scene.scene_id:
        raise ValueError("A revision cannot change the scene identity.")
    if not child.changed_paths:
        raise ValueError("Later revisions must declare changed paths.")


def save_scene_revision(
    db: firestore.Client,
    *,
    studio_project_id: str,
    source_attempt_id: str,
    revision: SceneRevision,
) -> bool:
    """Create one immutable revision; accept an identical retry."""
    for identifier in (
        studio_project_id,
        source_attempt_id,
        revision.revision_id,
    ):
        _validate_identifier(identifier)

    attempt = db.document(
        "projects",
        studio_project_id,
        "attempts",
        source_attempt_id,
    )
    attempt_snapshot = attempt.get(timeout=15)
    if not attempt_snapshot.exists:
        raise ValueError("Source attempt does not exist.")
    if attempt_snapshot.get("status") != "succeeded":
        raise ValueError("Source scene is not ready.")

    reference = attempt.collection(
        "scene_revisions"
    ).document(revision.revision_id)

    existing = reference.get(timeout=15)
    if existing.exists:
        if not _same_revision(existing, revision):
            raise ValueError(
                "Revision ID is already bound to different content."
            )
        return False

    if revision.version == 1:
        response = attempt.collection(
            "responses"
        ).document("final").get(timeout=15)

        if not response.exists:
            raise ValueError("Saved source scene is unavailable.")

        text = response.get("text")
        if not isinstance(text, str):
            raise ValueError("Saved source scene is invalid.")

        source_scene = SceneSpec.model_validate_json(text)
        if scene_sha256(source_scene) != revision.scene_sha256:
            raise ValueError(
                "Initial revision must match the saved source scene."
            )
    else:
        parent_reference = attempt.collection(
            "scene_revisions"
        ).document(revision.parent_revision_id)
        parent_snapshot = parent_reference.get(timeout=15)

        if not parent_snapshot.exists:
            raise ValueError("Parent revision does not exist.")

        _validate_parent(
            _parse_revision(parent_snapshot),
            revision,
        )

    payload = revision.model_dump(mode="json")

    try:
        reference.create(
            payload | {"created_at": firestore.SERVER_TIMESTAMP},
            timeout=15,
        )
    except Conflict:
        raced = reference.get(timeout=15)
        if not raced.exists or not _same_revision(raced, revision):
            raise ValueError(
                "Revision ID is already bound to different content."
            ) from None
        return False

    return True


def read_scene_revision(
    db: firestore.Client,
    *,
    studio_project_id: str,
    source_attempt_id: str,
    revision_id: str,
) -> SceneRevision:
    for identifier in (
        studio_project_id,
        source_attempt_id,
        revision_id,
    ):
        _validate_identifier(identifier)

    snapshot = db.document(
        "projects",
        studio_project_id,
        "attempts",
        source_attempt_id,
        "scene_revisions",
        revision_id,
    ).get(timeout=15)

    if not snapshot.exists:
        raise ValueError("Scene revision does not exist.")

    return _parse_revision(snapshot)


def list_scene_revisions(
    db: firestore.Client,
    *,
    studio_project_id: str,
    source_attempt_id: str,
) -> tuple[SceneRevision, ...]:
    _validate_identifier(studio_project_id)
    _validate_identifier(source_attempt_id)

    collection = db.collection(
        "projects",
        studio_project_id,
        "attempts",
        source_attempt_id,
        "scene_revisions",
    )
    query = collection.order_by("version").limit(100)
    return tuple(
        _parse_revision(snapshot)
        for snapshot in query.stream(timeout=15)
    )
