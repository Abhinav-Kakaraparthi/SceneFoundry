"""Firestore persistence for verified SceneFoundry users."""

from google.api_core.exceptions import Conflict
from google.cloud import firestore

from scenefoundry.domain.user import VerifiedUser


def _user_document(db, uid: str):
    return db.document("users", uid)


def _parse_user(snapshot) -> VerifiedUser:
    payload = snapshot.to_dict()
    if payload is None:
        raise ValueError("Verified user does not exist.")

    payload.pop("created_at", None)
    payload.pop("last_login_at", None)
    user = VerifiedUser.model_validate(payload)

    if user.uid != snapshot.id:
        raise ValueError(
            "Verified user document identity is inconsistent."
        )

    return user


def read_verified_user(
    db,
    *,
    uid: str,
) -> VerifiedUser:
    """Read one server-verified user profile."""

    snapshot = _user_document(db, uid).get(timeout=15)
    if not snapshot.exists:
        raise ValueError("Verified user does not exist.")
    return _parse_user(snapshot)


def _validate_existing_user(
    snapshot,
    expected: VerifiedUser,
) -> VerifiedUser:
    existing = _parse_user(snapshot)

    if (
        existing.uid != expected.uid
        or existing.provider != expected.provider
        or existing.email != expected.email
    ):
        raise ValueError(
            "Google identity conflicts with the stored user."
        )

    return existing


def _refresh_user(
    reference,
    existing: VerifiedUser,
    current: VerifiedUser,
) -> None:
    updates: dict[str, object] = {
        "last_login_at": firestore.SERVER_TIMESTAMP,
    }

    if existing.name != current.name:
        updates["name"] = current.name
    if existing.picture_url != current.picture_url:
        updates["picture_url"] = current.picture_url

    reference.update(updates, timeout=15)


def save_verified_user(
    db,
    *,
    user: VerifiedUser,
) -> bool:
    """Create a verified user or refresh an identical identity."""

    reference = _user_document(db, user.uid)
    existing_snapshot = reference.get(timeout=15)

    if existing_snapshot.exists:
        existing = _validate_existing_user(
            existing_snapshot,
            user,
        )
        _refresh_user(reference, existing, user)
        return False

    payload = user.model_dump(mode="json")
    payload["created_at"] = firestore.SERVER_TIMESTAMP
    payload["last_login_at"] = firestore.SERVER_TIMESTAMP

    try:
        reference.create(payload, timeout=15)
    except Conflict:
        raced = reference.get(timeout=15)
        if not raced.exists:
            raise

        existing = _validate_existing_user(raced, user)
        _refresh_user(reference, existing, user)
        return False

    return True
