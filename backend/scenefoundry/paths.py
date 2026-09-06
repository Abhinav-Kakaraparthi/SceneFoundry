"""Portable local workspace paths for temporary media processing."""

import os
from pathlib import Path
import tempfile


def local_data_root() -> Path:
    """Return the configured desktop or ephemeral runtime data root."""
    configured = os.environ.get("SCENEFOUNDRY_DATA_DIR")
    if configured:
        root = Path(configured).expanduser()
        if not root.is_absolute():
            raise RuntimeError(
                "SCENEFOUNDRY_DATA_DIR must be an absolute path."
            )
    elif local_app_data := os.environ.get("LOCALAPPDATA"):
        root = Path(local_app_data) / "SceneFoundry"
    else:
        root = Path(tempfile.gettempdir()) / "scenefoundry"

    root.mkdir(parents=True, exist_ok=True)
    return root
