import re

from google.cloud import firestore

from scenefoundry.domain.director_grounding import (
    DirectorGrounding,
)


def find_latest_scene_attempt(
    db: firestore.Client,
    *,
    studio_project_id: str,
) -> str | None:
    """Return the newest completed attempt containing a scene revision."""
    if not re.fullmatch(
        r"[A-Za-z0-9_-]{1,64}",
        studio_project_id,
    ):
        raise ValueError("Invalid project identifier.")

    attempts = db.collection(
        "projects",
        studio_project_id,
        "attempts",
    )
    query = attempts.order_by(
        "created_at",
        direction=firestore.Query.DESCENDING,
    ).limit(50)

    for snapshot in query.stream(timeout=15):
        if snapshot.get("status") != "succeeded":
            continue
        revision = next(
            snapshot.reference.collection("scene_revisions")
            .limit(1)
            .stream(timeout=15),
            None,
        )
        if revision is not None:
            return snapshot.id

    return None

def create_attempt(
    db: firestore.Client,
    *,
    studio_project_id: str,
    attempt_id: str,
    model: str,
    grounding: DirectorGrounding | None = None,
) -> None:
    """Create a planned attempt; raise a conflict if its ID already exists."""
    for identifier in (studio_project_id, attempt_id):
        if not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", identifier):
            raise ValueError("Invalid project or attempt identifier.")
    if not model.strip():
        raise ValueError("Model must not be blank.")

    if (
        grounding is not None
        and grounding.studio_project_id != studio_project_id
    ):
        raise ValueError(
            "Research grounding belongs to another project."
        )

    reference = db.document(
        "projects",
        studio_project_id,
        "attempts",
        attempt_id,
    )
    payload: dict[str, object] = {
        "status": "planned",
        "model": model,
        "created_at": firestore.SERVER_TIMESTAMP,
        "usage": None,
        "cost_micro_usd": None,
    }
    if grounding is not None:
        payload["grounding"] = grounding.model_dump(
            mode="json"
        )

    reference.create(
        payload,
        timeout=15,
    )


def claim_attempt(
    db: firestore.Client,
    *,
    studio_project_id: str,
    attempt_id: str,
    reservation_micro_usd: int,
) -> bool:
    """Atomically reserve funds and claim a planned attempt."""
    for identifier in (studio_project_id, attempt_id):
        if not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", identifier):
            raise ValueError("Invalid project or attempt identifier.")
    if type(reservation_micro_usd) is not int:
        raise TypeError("Reservation must be integer microdollars.")
    if not 0 < reservation_micro_usd <= 2**63 - 1:
        raise ValueError("Reservation must be a positive Firestore integer.")

    attempt = db.document(
        "projects", studio_project_id, "attempts", attempt_id
    )
    budget = db.document(
        "projects", studio_project_id, "budget", "current"
    )

    @firestore.transactional
    def claim(transaction):
        attempt_snapshot = attempt.get(transaction=transaction, timeout=15)
        if not attempt_snapshot.exists:
            raise ValueError("Attempt does not exist.")
        if attempt_snapshot.get("status") != "planned":
            return False

        budget_snapshot = budget.get(transaction=transaction, timeout=15)
        if not budget_snapshot.exists:
            raise ValueError("Project budget does not exist.")

        reserved = budget_snapshot.get("reserved_micro_usd")
        available = (
            budget_snapshot.get("allowance_micro_usd")
            - budget_snapshot.get("accounted_micro_usd")
            - reserved
        )
        if reservation_micro_usd > available:
            raise ValueError("Insufficient available budget.")

        transaction.update(
            budget,
            {"reserved_micro_usd": reserved + reservation_micro_usd},
        )
        transaction.update(
            attempt,
            {
                "status": "running",
                "reservation_micro_usd": reservation_micro_usd,
                "started_at": firestore.SERVER_TIMESTAMP,
            },
        )
        return True

    return claim(db.transaction())
