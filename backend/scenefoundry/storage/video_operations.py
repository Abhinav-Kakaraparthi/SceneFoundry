"""Immutable provider operation binding for a video attempt."""

import re

from google.api_core.exceptions import Conflict
from google.cloud import firestore
from google.cloud.firestore_v1 import DocumentReference

from scenefoundry.video.veo_config import VEO_LOCATION, VEO_MODEL


def save_video_operation(
    attempt: DocumentReference,
    operation_name: str,
) -> bool:
    """Bind a submitted Veo operation; return False for an identical retry."""
    pattern = (
        rf"projects/[^/\s]+/locations/{re.escape(VEO_LOCATION)}/"
        rf"publishers/google/models/{re.escape(VEO_MODEL)}/"
        r"operations/[A-Za-z0-9_-]+"
    )
    if not isinstance(operation_name, str) or not re.fullmatch(
        pattern, operation_name
    ):
        raise ValueError("Expected a full operation name for the configured Veo model.")

    snapshot = attempt.get(timeout=15)
    if not snapshot.exists:
        raise ValueError("Video attempt does not exist.")
    if snapshot.to_dict().get("model") != VEO_MODEL:
        raise ValueError("Attempt model does not match the Veo operation.")

    reference = attempt.collection("provider").document("operation")
    try:
        reference.create(
            {
                "operation_name": operation_name,
                "created_at": firestore.SERVER_TIMESTAMP,
            },
            timeout=15,
        )
        return True
    except Conflict:
        existing = reference.get(timeout=15).to_dict()
        if existing and existing.get("operation_name") == operation_name:
            return False
        raise ValueError("Attempt already has a different video operation.") from None
