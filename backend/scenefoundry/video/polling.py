"""Read an existing Veo operation without submitting another request."""

import re

from google import genai
from google.genai import types

from scenefoundry.video.veo_config import VEO_LOCATION, VEO_MODEL


def poll_veo(
    client: genai.Client,
    operation_name: str,
    *,
    project_id: str,
) -> types.GenerateVideosOperation:
    """Fetch once and preserve the provider's completion, result, and error."""
    prefix = (
        f"projects/{project_id}/locations/{VEO_LOCATION}/"
        f"publishers/google/models/{VEO_MODEL}/operations/"
    )
    if (
        not isinstance(project_id, str)
        or not project_id.strip()
        or not isinstance(operation_name, str)
        or not re.fullmatch(
            re.escape(prefix) + r"[A-Za-z0-9_-]+", operation_name
        )
    ):
        raise ValueError("Operation must match the Veo client's project and region.")

    return client.operations.get(
        types.GenerateVideosOperation(name=operation_name)
    )
