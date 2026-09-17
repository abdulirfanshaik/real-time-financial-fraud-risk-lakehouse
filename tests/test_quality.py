from __future__ import annotations

import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from risk_lakehouse.quality import validate_event


class QualityValidationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.required = [
            "event_id",
            "transaction_id",
            "customer_id",
            "account_id",
            "card_id",
            "event_ts",
            "ingest_ts",
            "amount",
            "currency",
            "merchant_id",
            "merchant_category",
            "merchant_country",
            "customer_country",
            "device_id",
            "channel",
            "decision",
            "source_system",
        ]
        self.event = {
            "event_id": "EVT1",
            "transaction_id": "TXN1",
            "customer_id": "CUS1",
            "account_id": "ACC1",
            "card_id": "CRD1",
            "event_ts": "2026-01-01T00:00:00Z",
            "ingest_ts": "2026-01-01T00:00:01Z",
            "amount": 50.0,
            "currency": "USD",
            "merchant_id": "MER1",
            "merchant_category": "GROCERY",
            "merchant_country": "US",
            "customer_country": "US",
            "device_id": "DEV1",
            "channel": "ECOMMERCE",
            "decision": "APPROVED",
            "source_system": "CARD_AUTHORIZATION",
        }

    def test_valid_event_passes(self) -> None:
        self.assertEqual(validate_event(self.event, self.required), [])

    def test_negative_amount_and_bad_timestamp_are_rejected(self) -> None:
        event = dict(self.event)
        event["amount"] = -1
        event["event_ts"] = "bad-time"
        errors = validate_event(event, self.required)
        self.assertIn("amount_must_be_positive", errors)
        self.assertIn("invalid_timestamp:event_ts", errors)


if __name__ == "__main__":
    unittest.main()

