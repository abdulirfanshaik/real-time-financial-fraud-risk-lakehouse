from __future__ import annotations

import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from risk_lakehouse.risk import score_transaction, severity


class RiskScoringTests(unittest.TestCase):
    def test_high_value_new_device_and_velocity_create_high_alert(self) -> None:
        event = {
            "amount": "5000.00",
            "merchant_category": "CRYPTO",
            "merchant_country": "HRC",
            "device_id": "NEW_DEVICE",
            "decision": "APPROVED",
        }
        card = {"primary_device_id": "KNOWN_DEVICE"}
        customer = {"country": "US", "risk_tier": "MEDIUM"}
        config = {
            "high_value_amount": 2000,
            "high_risk_categories": ["CRYPTO", "GAMBLING"],
            "demo_high_risk_countries": ["HRC"],
            "velocity_count_threshold": 4,
            "alert_score_threshold": 60,
            "high_severity_threshold": 80,
        }
        score, reasons = score_transaction(event, card, customer, 5, config)
        self.assertEqual(score, 100)
        self.assertEqual(severity(score, config), "HIGH")
        self.assertIn("high_velocity", reasons)
        self.assertIn("new_device", reasons)


if __name__ == "__main__":
    unittest.main()

