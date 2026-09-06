"""Atomic settlement using the video attempt's saved pricing estimate."""

import re
from random import uniform
from time import sleep

from google.api_core.exceptions import Aborted
from google.cloud import firestore

from scenefoundry.video.veo_config import VEO_MODEL


def settle_video(
    db: firestore.Client,
    *,
    studio_project_id: str,
    attempt_id: str,
    receipt_sha256: str,
) -> bool:
    """Charge one returned video at the saved request rate, once."""
    for identifier in (studio_project_id, attempt_id):
        if not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", identifier):
            raise ValueError("Invalid project or attempt identifier.")
    if not re.fullmatch(r"[0-9a-f]{64}", receipt_sha256):
        raise ValueError("Invalid receipt hash.")

    attempt = db.document("projects", studio_project_id, "attempts", attempt_id)
    budget = db.document("projects", studio_project_id, "budget", "current")
    charge = db.document("projects", studio_project_id, "charges", attempt_id)

    @firestore.transactional
    def settle(transaction):
        existing = charge.get(transaction=transaction, timeout=15)
        if existing.exists:
            stored = existing.to_dict()
            if (
                stored.get("basis") != "video_duration_estimate"
                or stored.get("receipt_sha256") != receipt_sha256
            ):
                raise ValueError("Attempt already has a conflicting settlement.")
            return False

        attempt_snapshot = attempt.get(transaction=transaction, timeout=15)
        budget_snapshot = budget.get(transaction=transaction, timeout=15)
        if not attempt_snapshot.exists or not budget_snapshot.exists:
            raise ValueError("Attempt or budget does not exist.")

        data = attempt_snapshot.to_dict()
        balances = budget_snapshot.to_dict()
        if (
            data.get("status") != "running"
            or data.get("kind") != "veo_video"
            or data.get("model") != VEO_MODEL
        ):
            raise ValueError("Expected a claimed Veo video attempt.")

        config = data["video_config"]
        rate = data["pricing_estimate"]
        seconds = config["duration_seconds"]
        unit_price = rate["micro_usd_per_second"]
        if (
            type(seconds) is not int or seconds not in (4, 6, 8)
            or type(unit_price) is not int or unit_price <= 0
            or config.get("number_of_videos") != 1
            or config.get("resolution") != "720p"
            or config.get("generate_audio") is not True
        ):
            raise ValueError("Unsupported saved video pricing configuration.")

        cost = seconds * unit_price
        if cost != data["estimated_cost_micro_usd"]:
            raise ValueError("Saved price and estimated cost disagree.")

        reservation = data["reservation_micro_usd"]
        reserved = balances["reserved_micro_usd"]
        accounted = balances["accounted_micro_usd"]
        if any(type(value) is not int for value in (reservation, reserved, accounted)):
            raise ValueError("Balances must be integer microdollars.")
        if reservation <= 0 or reserved < reservation or accounted < 0:
            raise ValueError("Inconsistent budget balances.")
        if accounted + cost > 2**63 - 1:
            raise ValueError("Calculated balance exceeds Firestore integer capacity.")

        transaction.create(charge, {
            "attempt_id": attempt_id,
            "basis": "video_duration_estimate",
            "cost_micro_usd": cost,
            "requested_seconds": seconds,
            "rate": rate,
            "receipt_sha256": receipt_sha256,
            "created_at": firestore.SERVER_TIMESTAMP,
        })
        transaction.update(budget, {
            "reserved_micro_usd": reserved - reservation,
            "accounted_micro_usd": accounted + cost,
        })
        transaction.update(attempt, {
            "reservation_micro_usd": 0,
            "cost_micro_usd": cost,
            "billing_status": "video_duration_estimate",
        })
        return True

    for retry_number in range(4):
        try:
            return settle(db.transaction())
        except Aborted:
            if retry_number == 3:
                raise
            sleep(uniform(0.1, 0.3) * 2**retry_number)
