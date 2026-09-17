from __future__ import annotations

from collections import defaultdict, deque
from datetime import datetime, timedelta


class VelocityTracker:
    def __init__(self, window_minutes: int) -> None:
        self.window = timedelta(minutes=window_minutes)
        self.events: dict[str, deque[datetime]] = defaultdict(deque)

    def record(self, card_id: str, event_ts: datetime) -> int:
        queue = self.events[card_id]
        cutoff = event_ts - self.window
        while queue and queue[0] < cutoff:
            queue.popleft()
        queue.append(event_ts)
        return len(queue)


def score_transaction(
    event: dict,
    card: dict,
    customer: dict,
    velocity_count: int,
    config: dict,
) -> tuple[int, list[str]]:
    reasons: list[str] = []
    score = 0
    amount = float(event["amount"])

    if amount >= float(config["high_value_amount"]):
        score += 35
        reasons.append("high_value_transaction")
    if event["merchant_category"] in set(config["high_risk_categories"]):
        score += 25
        reasons.append("high_risk_merchant_category")
    if event["merchant_country"] in set(config["demo_high_risk_countries"]):
        score += 25
        reasons.append("high_risk_country")
    elif event["merchant_country"] != customer["country"]:
        score += 15
        reasons.append("cross_border_transaction")
    if event["device_id"] != card["primary_device_id"]:
        score += 20
        reasons.append("new_device")
    if event["decision"] == "DECLINED":
        score += 10
        reasons.append("declined_authorization")
    if velocity_count >= int(config["velocity_count_threshold"]):
        score += 30
        reasons.append("high_velocity")
    if customer["risk_tier"] == "HIGH":
        score += 10
        reasons.append("elevated_customer_risk")

    return min(score, 100), reasons


def severity(score: int, config: dict) -> str:
    if score >= int(config["high_severity_threshold"]):
        return "HIGH"
    if score >= int(config["alert_score_threshold"]):
        return "MEDIUM"
    return "NONE"

