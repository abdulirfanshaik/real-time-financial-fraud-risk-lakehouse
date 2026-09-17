"""Publish generated card-authorization events to Kafka.

Install the optional dependency with `pip install kafka-python` before running.
"""

from __future__ import annotations

import argparse
import json
import os
import time
from pathlib import Path


def publish(input_path: Path, bootstrap_servers: str, topic: str, delay_ms: int) -> int:
    try:
        from kafka import KafkaProducer
    except ImportError as exc:
        raise SystemExit("Install kafka-python to run the streaming producer") from exc

    producer = KafkaProducer(
        bootstrap_servers=bootstrap_servers.split(","),
        key_serializer=lambda value: value.encode("utf-8"),
        value_serializer=lambda value: json.dumps(value).encode("utf-8"),
        acks="all",
        enable_idempotence=True,
    )
    count = 0
    with input_path.open("r", encoding="utf-8") as handle:
        for line in handle:
            event = json.loads(line)
            producer.send(topic, key=event.get("card_id", "unknown"), value=event)
            count += 1
            if delay_ms:
                time.sleep(delay_ms / 1000)
    producer.flush()
    producer.close()
    return count


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=Path("data/raw/card_authorizations.jsonl"))
    parser.add_argument("--bootstrap-servers", default=os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092"))
    parser.add_argument("--topic", default=os.getenv("KAFKA_TOPIC", "financial.card_authorizations.v1"))
    parser.add_argument("--delay-ms", type=int, default=0)
    args = parser.parse_args()
    count = publish(args.input, args.bootstrap_servers, args.topic, args.delay_ms)
    print(f"Published {count} events to {args.topic}")


if __name__ == "__main__":
    main()

