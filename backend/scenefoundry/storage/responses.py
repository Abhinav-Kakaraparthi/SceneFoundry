import re

from google.api_core.exceptions import Conflict
from google.cloud import firestore


def save_response(
    db: firestore.Client,
    *,
    studio_project_id: str,
    attempt_id: str,
    text: str,
    usage: list[dict[str, object]],
) -> bool:
    """Save a response once; accept identical retries and reject replacements."""
    for identifier in (studio_project_id, attempt_id):
        if not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", identifier):
            raise ValueError("Invalid project or attempt identifier.")

    reference = db.document(
        "projects", studio_project_id, "attempts", attempt_id,
        "responses", "final",
    )
    payload = {"text": text, "usage": usage}

    try:
        reference.create(
            payload | {"created_at": firestore.SERVER_TIMESTAMP},
            timeout=15,
        )
    except Conflict:
        existing = reference.get(timeout=15).to_dict()
        if existing is None or any(
            existing.get(key) != value for key, value in payload.items()
        ):
            raise ValueError("Attempt already has a different response.") from None
        return False

    return True