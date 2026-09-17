from __future__ import annotations

import argparse
import csv
import json
import shutil
import sqlite3
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

from .io_utils import read_csv, read_json, read_jsonl, write_csv, write_json
from .quality import parse_timestamp, quality_gate, validate_event
from .risk import VelocityTracker, score_transaction, severity


SILVER_FIELDS = [
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
    "customer_risk_tier",
    "is_late_event",
    "source_file",
    "source_line_number",
]

SCORED_FIELDS = SILVER_FIELDS + ["velocity_count_10m", "risk_score", "risk_reasons", "alert_severity"]


def _reset_output(output: Path) -> None:
    output.mkdir(parents=True, exist_ok=True)
    for name in ("bronze", "silver", "gold", "metrics"):
        target = output / name
        if target.exists():
            shutil.rmtree(target)
    database = output / "risk_lakehouse.db"
    if database.exists():
        database.unlink()


def _copy_bronze(input_dir: Path, output_dir: Path) -> None:
    bronze = output_dir / "bronze"
    bronze.mkdir(parents=True, exist_ok=True)
    for source in input_dir.iterdir():
        if source.is_file():
            shutil.copy2(source, bronze / source.name)


def _write_sqlite(database: Path, tables: dict[str, tuple[list[dict], list[str]]]) -> None:
    connection = sqlite3.connect(database)
    try:
        for table_name, (rows, fields) in tables.items():
            connection.execute(f'DROP TABLE IF EXISTS "{table_name}"')
            columns = ", ".join(f'"{field}" TEXT' for field in fields)
            connection.execute(f'CREATE TABLE "{table_name}" ({columns})')
            if rows:
                placeholders = ", ".join("?" for _ in fields)
                column_names = ", ".join(f'"{field}"' for field in fields)
                connection.executemany(
                    f'INSERT INTO "{table_name}" ({column_names}) VALUES ({placeholders})',
                    [[str(row.get(field, "")) for field in fields] for row in rows],
                )
        connection.commit()
    finally:
        connection.close()


def run_pipeline(input_dir: Path, output_dir: Path, config_path: Path) -> dict:
    config = read_json(config_path)
    risk_config = config["risk"]
    quality_config = config["quality"]
    _reset_output(output_dir)
    _copy_bronze(input_dir, output_dir)

    customers = {row["customer_id"]: row for row in read_csv(input_dir / "customers.csv")}
    accounts = {row["account_id"]: row for row in read_csv(input_dir / "accounts.csv")}
    cards = {row["card_id"]: row for row in read_csv(input_dir / "cards.csv")}

    source_file = input_dir / "card_authorizations.jsonl"
    rejected: list[dict] = []
    candidates: list[dict] = []
    seen_keys: set[tuple[str, str]] = set()
    duplicates_removed = 0
    physical_rows = 0
    late_events = 0

    for line_number, event in read_jsonl(source_file):
        physical_rows += 1
        errors = validate_event(event, quality_config["required_fields"])
        if not errors and event.get("customer_id") not in customers:
            errors.append("unknown_customer")
        if not errors and event.get("account_id") not in accounts:
            errors.append("unknown_account")
        if not errors and event.get("card_id") not in cards:
            errors.append("unknown_card")
        if errors:
            rejected.append(
                {
                    "source_file": source_file.name,
                    "source_line_number": line_number,
                    "event_id": event.get("event_id", ""),
                    "transaction_id": event.get("transaction_id", ""),
                    "rejection_reasons": "|".join(sorted(set(errors))),
                    "raw_record": json.dumps(event, sort_keys=True),
                }
            )
            continue

        key = (str(event["source_system"]), str(event["event_id"]))
        if key in seen_keys:
            duplicates_removed += 1
            continue
        seen_keys.add(key)

        event_ts = parse_timestamp(event["event_ts"])
        ingest_ts = parse_timestamp(event["ingest_ts"])
        is_late = int((ingest_ts - event_ts).total_seconds() > 15 * 60)
        late_events += is_late
        normalized = dict(event)
        normalized["amount"] = f"{float(event['amount']):.2f}"
        normalized["event_ts"] = event_ts.isoformat()
        normalized["ingest_ts"] = ingest_ts.isoformat()
        normalized["customer_risk_tier"] = customers[event["customer_id"]]["risk_tier"]
        normalized["is_late_event"] = is_late
        normalized["source_file"] = source_file.name
        normalized["source_line_number"] = line_number
        candidates.append(normalized)

    candidates.sort(key=lambda row: (row["event_ts"], row["event_id"]))
    velocity = VelocityTracker(int(risk_config["velocity_window_minutes"]))
    scored: list[dict] = []
    alerts: list[dict] = []

    for row in candidates:
        event_ts = parse_timestamp(row["event_ts"])
        velocity_count = velocity.record(row["card_id"], event_ts)
        score, reasons = score_transaction(
            row,
            cards[row["card_id"]],
            customers[row["customer_id"]],
            velocity_count,
            risk_config,
        )
        level = severity(score, risk_config)
        enriched = dict(row)
        enriched.update(
            {
                "velocity_count_10m": velocity_count,
                "risk_score": score,
                "risk_reasons": "|".join(reasons),
                "alert_severity": level,
            }
        )
        scored.append(enriched)
        if level != "NONE":
            alerts.append(
                {
                    "alert_id": f"ALT{len(alerts) + 1:09d}",
                    "event_id": row["event_id"],
                    "transaction_id": row["transaction_id"],
                    "customer_id": row["customer_id"],
                    "card_id": row["card_id"],
                    "event_ts": row["event_ts"],
                    "amount": row["amount"],
                    "risk_score": score,
                    "severity": level,
                    "reasons": "|".join(reasons),
                    "case_status": "OPEN",
                }
            )

    customer_stats: dict[str, dict] = {}
    for row in scored:
        stats = customer_stats.setdefault(
            row["customer_id"],
            {
                "customer_id": row["customer_id"],
                "customer_risk_tier": row["customer_risk_tier"],
                "transaction_count": 0,
                "total_amount": 0.0,
                "alert_count": 0,
                "max_risk_score": 0,
                "risk_score_total": 0,
                "latest_event_ts": row["event_ts"],
            },
        )
        stats["transaction_count"] += 1
        stats["total_amount"] += float(row["amount"])
        stats["alert_count"] += int(row["alert_severity"] != "NONE")
        stats["max_risk_score"] = max(stats["max_risk_score"], int(row["risk_score"]))
        stats["risk_score_total"] += int(row["risk_score"])
        stats["latest_event_ts"] = max(stats["latest_event_ts"], row["event_ts"])

    customer_360: list[dict] = []
    for stats in customer_stats.values():
        count = stats["transaction_count"]
        customer_360.append(
            {
                "customer_id": stats["customer_id"],
                "customer_risk_tier": stats["customer_risk_tier"],
                "transaction_count": count,
                "total_amount": f"{stats['total_amount']:.2f}",
                "alert_count": stats["alert_count"],
                "max_risk_score": stats["max_risk_score"],
                "average_risk_score": f"{stats['risk_score_total'] / count:.2f}",
                "latest_event_ts": stats["latest_event_ts"],
            }
        )
    customer_360.sort(key=lambda row: row["customer_id"])

    hourly: dict[str, dict] = defaultdict(lambda: {"transaction_count": 0, "alert_count": 0, "total_amount": 0.0})
    for row in scored:
        hour = parse_timestamp(row["event_ts"]).strftime("%Y-%m-%dT%H:00:00Z")
        hourly[hour]["transaction_count"] += 1
        hourly[hour]["alert_count"] += int(row["alert_severity"] != "NONE")
        hourly[hour]["total_amount"] += float(row["amount"])
    hourly_rows = [
        {
            "event_hour": hour,
            "transaction_count": values["transaction_count"],
            "alert_count": values["alert_count"],
            "alert_rate": f"{values['alert_count'] / values['transaction_count']:.6f}",
            "total_amount": f"{values['total_amount']:.2f}",
        }
        for hour, values in sorted(hourly.items())
    ]

    reject_rate = len(rejected) / physical_rows if physical_rows else 0.0
    duplicate_rate = duplicates_removed / physical_rows if physical_rows else 0.0
    metrics = {
        "physical_source_rows": physical_rows,
        "canonical_transactions": len(candidates),
        "rejected_records": len(rejected),
        "duplicates_removed": duplicates_removed,
        "late_events_observed": late_events,
        "fraud_risk_alerts": len(alerts),
        "high_severity_alerts": sum(1 for row in alerts if row["severity"] == "HIGH"),
        "medium_severity_alerts": sum(1 for row in alerts if row["severity"] == "MEDIUM"),
        "customer_risk_360_records": len(customer_360),
        "reject_rate": reject_rate,
        "duplicate_rate": duplicate_rate,
    }
    gate_status, gate_failures = quality_gate(metrics, quality_config)
    metrics["quality_gate"] = gate_status
    metrics["quality_gate_failures"] = gate_failures
    metrics["completed_at"] = datetime.now(timezone.utc).isoformat()

    silver_dir = output_dir / "silver"
    gold_dir = output_dir / "gold"
    metrics_dir = output_dir / "metrics"
    write_csv(silver_dir / "transactions.csv", candidates, SILVER_FIELDS)
    write_csv(
        silver_dir / "rejected_records.csv",
        rejected,
        ["source_file", "source_line_number", "event_id", "transaction_id", "rejection_reasons", "raw_record"],
    )
    write_csv(gold_dir / "risk_scored_transactions.csv", scored, SCORED_FIELDS)
    alert_fields = ["alert_id", "event_id", "transaction_id", "customer_id", "card_id", "event_ts", "amount", "risk_score", "severity", "reasons", "case_status"]
    write_csv(gold_dir / "fraud_alerts.csv", alerts, alert_fields)
    customer_fields = ["customer_id", "customer_risk_tier", "transaction_count", "total_amount", "alert_count", "max_risk_score", "average_risk_score", "latest_event_ts"]
    write_csv(gold_dir / "customer_risk_360.csv", customer_360, customer_fields)
    hourly_fields = ["event_hour", "transaction_count", "alert_count", "alert_rate", "total_amount"]
    write_csv(gold_dir / "hourly_risk_metrics.csv", hourly_rows, hourly_fields)
    write_json(metrics_dir / "quality_report.json", {"metrics": metrics, "thresholds": quality_config})
    write_json(
        metrics_dir / "pipeline_manifest.json",
        {
            "project_name": config["project_name"],
            "input": str(input_dir),
            "output": str(output_dir),
            "layers": ["bronze", "silver", "gold"],
            "generated_tables": ["silver_transactions", "fraud_alerts", "customer_risk_360"],
        },
    )

    _write_sqlite(
        output_dir / "risk_lakehouse.db",
        {
            "silver_transactions": (candidates, SILVER_FIELDS),
            "fraud_alerts": (alerts, alert_fields),
            "customer_risk_360": (customer_360, customer_fields),
        },
    )
    return metrics


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the local financial fraud and risk lakehouse")
    parser.add_argument("--input", type=Path, default=Path("data/raw"))
    parser.add_argument("--output", type=Path, default=Path("data/processed"))
    parser.add_argument("--config", type=Path, default=Path("config/project.json"))
    args = parser.parse_args()
    metrics = run_pipeline(args.input, args.output, args.config)
    print(json.dumps(metrics, indent=2, sort_keys=True))
    if metrics["quality_gate"] != "PASS":
        raise SystemExit(2)


if __name__ == "__main__":
    main()

