from __future__ import annotations

import argparse
import random
from datetime import datetime, timedelta, timezone
from pathlib import Path

from .io_utils import write_csv, write_json, write_jsonl


COUNTRIES = ["US", "CA", "GB", "DE", "SG", "IN"]
MERCHANT_CATEGORIES = ["GROCERY", "TRAVEL", "RETAIL", "FUEL", "DINING", "CRYPTO", "GAMBLING"]
CHANNELS = ["CARD_PRESENT", "ECOMMERCE", "MOBILE_WALLET"]


def generate_dataset(
    output: Path,
    customer_count: int = 500,
    account_count: int = 750,
    card_count: int = 1000,
    transaction_count: int = 5000,
    seed: int = 20260917,
) -> dict:
    rng = random.Random(seed)
    output.mkdir(parents=True, exist_ok=True)

    customers: list[dict] = []
    for index in range(customer_count):
        risk_tier = rng.choices(["LOW", "MEDIUM", "HIGH"], weights=[76, 20, 4], k=1)[0]
        customers.append(
            {
                "customer_id": f"CUS{index + 1:06d}",
                "country": rng.choice(COUNTRIES),
                "risk_tier": risk_tier,
                "kyc_status": "VERIFIED" if index % 97 else "REVIEW",
                "segment": rng.choice(["MASS", "AFFLUENT", "SMALL_BUSINESS"]),
            }
        )

    accounts: list[dict] = []
    for index in range(account_count):
        customer = customers[index % customer_count]
        accounts.append(
            {
                "account_id": f"ACC{index + 1:07d}",
                "customer_id": customer["customer_id"],
                "account_type": rng.choice(["CHECKING", "SAVINGS", "CREDIT"]),
                "status": "ACTIVE",
                "opened_date": f"{rng.randint(2016, 2025)}-{rng.randint(1, 12):02d}-{rng.randint(1, 28):02d}",
            }
        )

    cards: list[dict] = []
    for index in range(card_count):
        account = accounts[index % account_count]
        cards.append(
            {
                "card_id": f"CRD{index + 1:07d}",
                "account_id": account["account_id"],
                "customer_id": account["customer_id"],
                "card_type": rng.choice(["DEBIT", "CREDIT"]),
                "primary_device_id": f"DEV{index + 1:07d}",
                "status": "ACTIVE",
            }
        )

    customers_by_id = {row["customer_id"]: row for row in customers}
    start = datetime(2026, 9, 15, 13, 0, tzinfo=timezone.utc)
    events: list[dict] = []

    for index in range(transaction_count):
        # Regularly reuse one card for six events to create deterministic velocity bursts.
        if index % 250 < 6:
            card = cards[(index // 250) % card_count]
        else:
            card = rng.choice(cards)
        customer = customers_by_id[card["customer_id"]]
        event_ts = start + timedelta(seconds=index * 3)
        is_attack_pattern = index % 67 == 0
        is_high_value = index % 37 == 0 or is_attack_pattern
        is_high_risk_category = index % 43 == 0 or is_attack_pattern
        is_high_risk_country = index % 97 == 0 or is_attack_pattern
        is_new_device = index % 41 == 0 or is_attack_pattern
        is_declined = index % 29 == 0
        is_late = index % 23 == 0

        amount = round(rng.uniform(5, 480), 2)
        if is_high_value:
            amount = round(rng.uniform(2200, 7200), 2)
        category = rng.choice(MERCHANT_CATEGORIES[:5])
        if is_high_risk_category:
            category = rng.choice(["CRYPTO", "GAMBLING"])
        merchant_country = customer["country"] if index % 7 else rng.choice(COUNTRIES)
        if is_high_risk_country:
            merchant_country = "HRC"
        ingest_delay = timedelta(minutes=30) if is_late else timedelta(seconds=rng.randint(1, 240))

        events.append(
            {
                "event_id": f"EVT{index + 1:09d}",
                "transaction_id": f"TXN{index + 1:09d}",
                "customer_id": card["customer_id"],
                "account_id": card["account_id"],
                "card_id": card["card_id"],
                "event_ts": event_ts.isoformat().replace("+00:00", "Z"),
                "ingest_ts": (event_ts + ingest_delay).isoformat().replace("+00:00", "Z"),
                "amount": amount,
                "currency": "USD",
                "merchant_id": f"MER{rng.randint(1, 800):06d}",
                "merchant_category": category,
                "merchant_country": merchant_country,
                "customer_country": customer["country"],
                "device_id": f"NEWDEV{index + 1:07d}" if is_new_device else card["primary_device_id"],
                "channel": rng.choice(CHANNELS),
                "decision": "DECLINED" if is_declined else "APPROVED",
                "source_system": "CARD_AUTHORIZATION",
            }
        )

    duplicate_count = max(1, transaction_count // 50)
    duplicate_indices = rng.sample(range(transaction_count), k=min(duplicate_count, transaction_count))
    duplicates = [dict(events[index]) for index in duplicate_indices]
    for offset, event in enumerate(duplicates, 1):
        original_ingest = datetime.fromisoformat(event["ingest_ts"].replace("Z", "+00:00"))
        event["ingest_ts"] = (original_ingest + timedelta(minutes=5, seconds=offset)).isoformat().replace("+00:00", "Z")

    malformed_count = max(3, transaction_count // 1000)
    malformed: list[dict] = []
    for index in range(malformed_count):
        bad = dict(events[index])
        bad["event_id"] = f"BAD{index + 1:06d}"
        bad["transaction_id"] = f"BADTXN{index + 1:06d}"
        if index % 3 == 0:
            bad["event_ts"] = "not-a-timestamp"
        elif index % 3 == 1:
            bad["amount"] = -25.0
        else:
            bad["customer_id"] = ""
        malformed.append(bad)

    physical_events = events + duplicates + malformed
    rng.shuffle(physical_events)

    write_csv(output / "customers.csv", customers, list(customers[0]))
    write_csv(output / "accounts.csv", accounts, list(accounts[0]))
    write_csv(output / "cards.csv", cards, list(cards[0]))
    write_jsonl(output / "card_authorizations.jsonl", physical_events)

    manifest = {
        "seed": seed,
        "customers": customer_count,
        "accounts": account_count,
        "cards": card_count,
        "logical_transactions": transaction_count,
        "physical_event_rows": len(physical_events),
        "injected_duplicates": len(duplicates),
        "injected_malformed_rows": len(malformed),
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
    write_json(output / "manifest.json", manifest)
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate deterministic financial authorization events")
    parser.add_argument("--output", type=Path, default=Path("data/raw"))
    parser.add_argument("--customers", type=int, default=500)
    parser.add_argument("--accounts", type=int, default=750)
    parser.add_argument("--cards", type=int, default=1000)
    parser.add_argument("--transactions", type=int, default=5000)
    parser.add_argument("--seed", type=int, default=20260917)
    args = parser.parse_args()
    manifest = generate_dataset(
        args.output,
        args.customers,
        args.accounts,
        args.cards,
        args.transactions,
        args.seed,
    )
    print(f"Generated {manifest['physical_event_rows']} physical rows for {manifest['logical_transactions']} logical transactions")


if __name__ == "__main__":
    main()
