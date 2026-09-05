import re
from random import uniform
from time import sleep

from google.api_core.exceptions import Aborted
from google.cloud import firestore

from scenefoundry.billing.rates import TokenRateCard


def settle_attempt(
    db: firestore.Client,
    *,
    studio_project_id: str,
    attempt_id: str,
    cost_micro_usd: int,
    rate: TokenRateCard,
) -> bool:
    """Record a calculated charge once and release its reservation."""
    for identifier in (studio_project_id, attempt_id):
        if not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", identifier):
            raise ValueError("Invalid project or attempt identifier.")
    if type(cost_micro_usd) is not int:
        raise TypeError("Cost must be integer microdollars.")
    if not 0 <= cost_micro_usd <= 2**63 - 1:
        raise ValueError("Cost must fit a nonnegative Firestore integer.")

    attempt = db.document("projects", studio_project_id, "attempts", attempt_id)
    budget = db.document("projects", studio_project_id, "budget", "current")
    charge = db.document("projects", studio_project_id, "charges", attempt_id)
    calculation = {
        "attempt_id": attempt_id,
        "cost_micro_usd": cost_micro_usd,
        "basis": "usage_calculated",
        "rate": rate.model_dump(mode="json"),
    }

    @firestore.transactional
    def settle(transaction):
        existing = charge.get(transaction=transaction, timeout=15)
        if existing.exists:
            stored = existing.to_dict()
            if any(stored.get(key) != value for key, value in calculation.items()):
                raise ValueError("Attempt already has a different charge.")
            return False

        attempt_snapshot = attempt.get(transaction=transaction, timeout=15)
        budget_snapshot = budget.get(transaction=transaction, timeout=15)
        if not attempt_snapshot.exists or not budget_snapshot.exists:
            raise ValueError("Attempt or budget does not exist.")
        if attempt_snapshot.get("status") != "running":
            raise ValueError("Only a claimed attempt can be settled.")
        if attempt_snapshot.get("model") != rate.model:
            raise ValueError("Rate card model does not match the attempt.")

        reservation = attempt_snapshot.get("reservation_micro_usd")
        reserved = budget_snapshot.get("reserved_micro_usd")
        accounted = budget_snapshot.get("accounted_micro_usd") + cost_micro_usd
        if reservation <= 0 or reserved < reservation:
            raise ValueError("Inconsistent reservation balance.")
        if accounted > 2**63 - 1:
            raise ValueError("Accounted spending exceeds Firestore integer capacity.")

        transaction.create(
            charge,
            calculation | {"created_at": firestore.SERVER_TIMESTAMP},
        )
        transaction.update(
            budget,
            {
                "reserved_micro_usd": reserved - reservation,
                "accounted_micro_usd": accounted,
            },
        )
        transaction.update(
            attempt,
            {
                "reservation_micro_usd": 0,
                "cost_micro_usd": cost_micro_usd,
                "billing_status": "usage_calculated",
            },
        )
        return True

    for retry_number in range(4):
        try:
            return settle(db.transaction())
        except Aborted:
            if retry_number == 3:
                raise
            sleep(uniform(0.1, 0.3) * 2**retry_number)