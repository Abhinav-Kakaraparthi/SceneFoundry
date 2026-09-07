from google.api_core.exceptions import AlreadyExists
from google.cloud import firestore

from scenefoundry.domain.artifacts import (
    ARTIFACT_ORDER,
    ArtifactStamp,
)
from scenefoundry.storage.revisions import read_scene_revision


_KIND_POSITION = {
    kind: position
    for position, kind in enumerate(ARTIFACT_ORDER)
}


def _artifact_document(
    db,
    *,
    studio_project_id: str,
    source_attempt_id: str,
    artifact_id: str,
):
    return db.document(
        "projects",
        studio_project_id,
        "attempts",
        source_attempt_id,
        "artifacts",
        artifact_id,
    )


def _artifact_collection(
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
        "artifacts",
    )


def _parse_stamp(snapshot) -> ArtifactStamp:
    payload = snapshot.to_dict()
    payload.pop("created_at", None)

    stamp = ArtifactStamp.model_validate(payload)
    if stamp.artifact_id != snapshot.id:
        raise ValueError("Artifact document identity is inconsistent.")
    return stamp


def _same_stamp(snapshot, expected: ArtifactStamp) -> bool:
    try:
        return _parse_stamp(snapshot) == expected
    except (TypeError, ValueError):
        return False


def read_artifact_stamp(
    db,
    *,
    studio_project_id: str,
    source_attempt_id: str,
    artifact_id: str,
) -> ArtifactStamp:
    snapshot = _artifact_document(
        db,
        studio_project_id=studio_project_id,
        source_attempt_id=source_attempt_id,
        artifact_id=artifact_id,
    ).get(timeout=15)

    if not snapshot.exists:
        raise ValueError(f"Artifact does not exist: {artifact_id}")

    return _parse_stamp(snapshot)


def _validate_inputs(
    db,
    *,
    studio_project_id: str,
    source_attempt_id: str,
    stamp: ArtifactStamp,
) -> None:
    input_ids = tuple(item.artifact_id for item in stamp.inputs)

    if len(input_ids) != len(set(input_ids)):
        raise ValueError("Artifact inputs must be unique.")
    if stamp.artifact_id in input_ids:
        raise ValueError("An artifact cannot depend on itself.")

    output_position = _KIND_POSITION[stamp.kind]

    for expected in stamp.inputs:
        if _KIND_POSITION[expected.kind] >= output_position:
            raise ValueError(
                "Artifact inputs must precede the output kind."
            )

        actual = read_artifact_stamp(
            db,
            studio_project_id=studio_project_id,
            source_attempt_id=source_attempt_id,
            artifact_id=expected.artifact_id,
        )

        if actual.kind != expected.kind:
            raise ValueError(
                f"Artifact input kind differs: {expected.artifact_id}"
            )
        if actual.sha256 != expected.sha256:
            raise ValueError(
                f"Artifact input hash differs: {expected.artifact_id}"
            )


def save_artifact_stamp(
    db,
    *,
    studio_project_id: str,
    source_attempt_id: str,
    stamp: ArtifactStamp,
) -> bool:
    """Create immutable provenance or accept an identical retry."""

    read_scene_revision(
        db,
        studio_project_id=studio_project_id,
        source_attempt_id=source_attempt_id,
        revision_id=stamp.revision_id,
    )
    _validate_inputs(
        db,
        studio_project_id=studio_project_id,
        source_attempt_id=source_attempt_id,
        stamp=stamp,
    )

    document = _artifact_document(
        db,
        studio_project_id=studio_project_id,
        source_attempt_id=source_attempt_id,
        artifact_id=stamp.artifact_id,
    )
    existing = document.get(timeout=15)

    if existing.exists:
        if _same_stamp(existing, stamp):
            return False
        raise ValueError(
            "Artifact already exists with different provenance."
        )

    payload = stamp.model_dump(mode="json")
    payload["created_at"] = firestore.SERVER_TIMESTAMP

    try:
        document.create(payload)
    except AlreadyExists:
        existing = document.get(timeout=15)
        if existing.exists and _same_stamp(existing, stamp):
            return False
        raise ValueError(
            "Artifact was concurrently created with different provenance."
        )

    return True


def list_artifact_stamps(
    db,
    *,
    studio_project_id: str,
    source_attempt_id: str,
    revision_id: str | None = None,
    scope_id: str | None = None,
) -> tuple[ArtifactStamp, ...]:
    stamps = tuple(
        _parse_stamp(snapshot)
        for snapshot in _artifact_collection(
            db,
            studio_project_id=studio_project_id,
            source_attempt_id=source_attempt_id,
        ).stream(timeout=15)
    )

    filtered = (
        stamp
        for stamp in stamps
        if revision_id is None or stamp.revision_id == revision_id
    )
    filtered = (
        stamp
        for stamp in filtered
        if scope_id is None or stamp.scope_id == scope_id
    )

    return tuple(
        sorted(
            filtered,
            key=lambda stamp: (
                _KIND_POSITION[stamp.kind],
                stamp.scope_id,
                stamp.artifact_id,
            ),
        )
    )
