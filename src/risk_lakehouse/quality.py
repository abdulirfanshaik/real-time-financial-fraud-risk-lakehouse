from __future__ import annotations

from datetime import datetime
from typing import Iterable


def parse_timestamp(value: object) -> datetime:
    if not isinstance(value, str) or not value.strip():
        raise ValueError("timestamp is missing")
    normalized = value.replace("Z", "+00:00")
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is None:
        raise ValueError("timestamp must include a timezone")
    return parsed


def validate_event(event: dict, required_fields: Iterable[str]) -> list[str]:
    errors: list[str] = []
    for field in required_fields:
        if field not in event or event[field] in (None, ""):
            errors.append(f"missing_required_field:{field}")

    try:
        amount = float(event.get("amount", ""))
        if amount <= 0:
            errors.append("amount_must_be_positive")
    except (TypeError, ValueError):
        errors.append("amount_not_numeric")

    for field in ("event_ts", "ingest_ts"):
        try:
            parse_timestamp(event.get(field))
        except (TypeError, ValueError):
            errors.append(f"invalid_timestamp:{field}")

    if event.get("decision") not in {"APPROVED", "DECLINED"}:
        errors.append("invalid_decision")

    if event.get("channel") not in {"CARD_PRESENT", "ECOMMERCE", "MOBILE_WALLET"}:
        errors.append("invalid_channel")

    return sorted(set(errors))


def quality_gate(metrics: dict, thresholds: dict) -> tuple[str, list[str]]:
    failures: list[str] = []
    if metrics["reject_rate"] > float(thresholds["max_reject_rate"]):
        failures.append("reject_rate_exceeded")
    if metrics["duplicate_rate"] > float(thresholds["max_duplicate_rate"]):
        failures.append("duplicate_rate_exceeded")
    return ("PASS" if not failures else "FAIL", failures)

