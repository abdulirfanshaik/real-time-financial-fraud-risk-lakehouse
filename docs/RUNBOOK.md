# Operations Runbook

## Service-level indicators

Monitor these signals in production:

- source-to-Bronze event latency;
- Kafka consumer lag by partition;
- processing throughput and batch duration;
- checkpoint age and failed micro-batches;
- reject and duplicate rates;
- late-event volume;
- Silver-to-Gold completeness;
- alert count and severity distribution;
- warehouse publication freshness.

## Quality gate failure

1. Open `data/processed/metrics/quality_report.json` or the production observability dashboard.
2. Identify whether the reject or duplicate threshold failed.
3. Group rejected records by source, reason and schema version.
4. Compare current rates with the prior successful interval.
5. Inspect a safe sample of Bronze payloads and producer metadata.
6. Correct the source contract, transformation or threshold only after confirming the cause.
7. Replay the affected Bronze interval into a versioned Silver target.
8. Compare record counts, amounts, duplicate counts and alert counts.
9. Promote the corrected version and document the incident.

## Kafka lag

1. Confirm broker and consumer-group health.
2. Check whether lag is isolated to a partition.
3. Review event size, skew, executor utilization and downstream write latency.
4. Scale consumers within the topic's partition limit.
5. Correct hot-key behavior or repartition before increasing infrastructure blindly.
6. Verify checkpoint progress and end-to-end latency after recovery.

## Schema change

1. Retain the unparsed payload in Bronze.
2. Compare the incoming schema with the registered contract.
3. Classify the change as compatible, conditionally compatible or breaking.
4. Add nullable fields through a reviewed schema-evolution path.
5. Route breaking records to quarantine until the mapping is deployed.
6. Backfill from Bronze and compare control totals.

## Duplicate spike

1. Confirm the deduplication key and time window.
2. Inspect producer retries, timeouts and idempotence settings.
3. Check whether a source restarted from an earlier offset or file watermark.
4. Preserve duplicates in Bronze while keeping Silver unique.
5. Validate that canonical counts remain stable after replay.

## Data recovery

The recovery order is Bronze replay, Silver validation, Gold rebuild and control comparison. Never repair Gold directly when the source or Silver transformation is wrong. Keep every corrected run versioned until the control owner approves promotion.

