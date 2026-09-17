from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from risk_lakehouse.generator import generate_dataset
from risk_lakehouse.pipeline import run_pipeline


class EndToEndPipelineTests(unittest.TestCase):
    def test_pipeline_is_deterministic_and_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            raw = root / "raw"
            processed = root / "processed"
            manifest = generate_dataset(
                raw,
                customer_count=100,
                account_count=150,
                card_count=200,
                transaction_count=1000,
                seed=77,
            )
            first = run_pipeline(raw, processed, PROJECT_ROOT / "config/project.json")
            second = run_pipeline(raw, processed, PROJECT_ROOT / "config/project.json")

            self.assertEqual(first["canonical_transactions"], 1000)
            self.assertEqual(first["duplicates_removed"], manifest["injected_duplicates"])
            self.assertEqual(first["rejected_records"], manifest["injected_malformed_rows"])
            self.assertGreater(first["fraud_risk_alerts"], 0)
            self.assertEqual(first["quality_gate"], "PASS")
            for field in (
                "canonical_transactions",
                "duplicates_removed",
                "rejected_records",
                "fraud_risk_alerts",
                "high_severity_alerts",
                "medium_severity_alerts",
            ):
                self.assertEqual(first[field], second[field])


if __name__ == "__main__":
    unittest.main()

