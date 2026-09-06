"""Regional, ADC-authenticated client for Veo operations."""

import google.auth
from google import genai
from google.genai import types

from scenefoundry.video.veo_config import VEO_LOCATION


def create_veo_client(project_id: str) -> genai.Client:
    """Create a caller-owned client with one HTTP attempt per request."""
    if not isinstance(project_id, str) or not project_id.strip():
        raise ValueError("Google Cloud project ID is required.")

    credentials, _ = google.auth.default(
        scopes=["https://www.googleapis.com/auth/cloud-platform"]
    )
    return genai.Client(
        enterprise=True,
        project=project_id.strip(),
        location=VEO_LOCATION,
        credentials=credentials,
        http_options=types.HttpOptions(
            api_version="v1",
            timeout=120_000,
            retry_options=types.HttpRetryOptions(attempts=1),
        ),
    )
