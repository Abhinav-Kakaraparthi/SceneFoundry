"""Immutable project-level screenplay version storage."""

import re

from google.api_core.exceptions import Conflict
from google.cloud import firestore

from scenefoundry.domain.screenplay import (
    ScreenplayVersion,
    screenplay_version_id,
)

_PROJECT_ID = re.compile(r"^[A-Za-z0-9_-]{1,64}$")


def _validate_project_id(value: str) -> None:
    if not isinstance(value, str) or not _PROJECT_ID.fullmatch(value):
        raise ValueError(f"Invalid studio project ID: {value!r}")


def _version_document(
    db,
    *,
    studio_project_id: str,
    screenplay_id: str,
    version_id: str,
):
    return db.document(
        "projects",
        studio_project_id,
        "screenplays",
        screenplay_id,
        "versions",
        version_id,
    )


def _version_collection(
    db,
    *,
    studio_project_id: str,
    screenplay_id: str,
):
    return db.collection(
        "projects",
        studio_project_id,
        "screenplays",
        screenplay_id,
        "versions",
    )


def _parse_version(
    snapshot,
    *,
    expected_screenplay_id: str,
) -> ScreenplayVersion:
    payload = snapshot.to_dict()
    if payload is None:
        raise ValueError("Screenplay version does not exist.")

    payload.pop("created_at", None)
    version = ScreenplayVersion.model_validate(payload)

    if version.version_id != snapshot.id:
        raise ValueError(
            "Screenplay version document identity is inconsistent."
        )
    if version.screenplay_id != expected_screenplay_id:
        raise ValueError(
            "Screenplay document scope is inconsistent."
        )

    return version


def _same_version(
    snapshot,
    expected: ScreenplayVersion,
) -> bool:
    try:
        actual = _parse_version(
            snapshot,
            expected_screenplay_id=expected.screenplay_id,
        )
    except (TypeError, ValueError):
        return False
    return actual == expected


def read_screenplay_version(
    db,
    *,
    studio_project_id: str,
    screenplay_id: str,
    version_id: str,
) -> ScreenplayVersion:
    _validate_project_id(studio_project_id)

    snapshot = _version_document(
        db,
        studio_project_id=studio_project_id,
        screenplay_id=screenplay_id,
        version_id=version_id,
    ).get(timeout=15)

    if not snapshot.exists:
        raise ValueError("Screenplay version does not exist.")

    return _parse_version(
        snapshot,
        expected_screenplay_id=screenplay_id,
    )


def save_screenplay_version(
    db,
    *,
    studio_project_id: str,
    version: ScreenplayVersion,
) -> bool:
    """Create one immutable linear version or accept an identical retry."""

    _validate_project_id(studio_project_id)

    expected_id = screenplay_version_id(
        version.screenplay_id,
        version.version,
    )
    if version.version_id != expected_id:
        raise ValueError(
            f"Version ID must be deterministic: {expected_id}"
        )

    reference = _version_document(
        db,
        studio_project_id=studio_project_id,
        screenplay_id=version.screenplay_id,
        version_id=version.version_id,
    )
    existing = reference.get(timeout=15)

    if existing.exists:
        if _same_version(existing, version):
            return False
        raise ValueError(
            "Screenplay version ID is bound to different content."
        )

    if version.version > 1:
        expected_parent_id = screenplay_version_id(
            version.screenplay_id,
            version.version - 1,
        )
        if version.parent_version_id != expected_parent_id:
            raise ValueError(
                "Screenplay parent must be the preceding version."
            )

        parent = read_screenplay_version(
            db,
            studio_project_id=studio_project_id,
            screenplay_id=version.screenplay_id,
            version_id=expected_parent_id,
        )
        if parent.version + 1 != version.version:
            raise ValueError(
                "Screenplay version must immediately follow its parent."
            )
        if parent.content_sha256 == version.content_sha256:
            raise ValueError(
                "A new screenplay version must change the content."
            )

    payload = version.model_dump(mode="json")
    payload["created_at"] = firestore.SERVER_TIMESTAMP

    try:
        reference.create(payload, timeout=15)
    except Conflict:
        raced = reference.get(timeout=15)
        if raced.exists and _same_version(raced, version):
            return False
        raise ValueError(
            "Screenplay version was concurrently created differently."
        ) from None

    return True


def list_screenplay_versions(
    db,
    *,
    studio_project_id: str,
    screenplay_id: str,
) -> tuple[ScreenplayVersion, ...]:
    _validate_project_id(studio_project_id)

    query = (
        _version_collection(
            db,
            studio_project_id=studio_project_id,
            screenplay_id=screenplay_id,
        )
        .order_by("version")
        .limit(100)
    )
    return tuple(
        _parse_version(
            snapshot,
            expected_screenplay_id=screenplay_id,
        )
        for snapshot in query.stream(timeout=15)
    )
