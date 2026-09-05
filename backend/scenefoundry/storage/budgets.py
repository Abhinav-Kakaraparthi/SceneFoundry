import re

from google.cloud import firestore


def create_budget(
    db: firestore.Client,
    *,
    studio_project_id: str,
    allowance_micro_usd: int,
) -> None:
    """Create a project budget without resetting an existing balance."""
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", studio_project_id):
        raise ValueError("Invalid project identifier.")
    if type(allowance_micro_usd) is not int:
        raise TypeError("Budget allowance must be integer microdollars.")
    if not 0 <= allowance_micro_usd <= 2**63 - 1:
        raise ValueError("Budget allowance must fit a nonnegative Firestore integer.")

    db.document(
        "projects", studio_project_id, "budget", "current"
    ).create(
        {
            "allowance_micro_usd": allowance_micro_usd,
            "accounted_micro_usd": 0,
            "reserved_micro_usd": 0,
            "created_at": firestore.SERVER_TIMESTAMP,
        },
        timeout=15,
    )