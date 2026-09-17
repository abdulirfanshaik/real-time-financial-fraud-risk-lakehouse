# Interview Guide

## Project positioning

This project supports a JPMorgan Chase data engineering discussion because it combines financial-event ingestion, fraud and risk analytics, governed lakehouse processing, near-real-time visibility, data quality, auditability, security, performance and production operations. It is intentionally different from the Axis Bank payment-reconciliation project: this project concentrates on card-authorization streaming and transaction-risk data products.

## Ninety-second introduction

I built a real-time financial fraud and risk lakehouse that processes card-authorization events from ingestion through trusted fraud-review datasets. The main challenge was that financial events can arrive duplicated, delayed, out of order or malformed, while fraud teams need timely and explainable signals. I designed a Bronze, Silver and Gold flow. Bronze preserves raw events and source metadata for audit and replay. Silver validates required fields, standardizes timestamps and amounts, checks customer, account and card references, removes duplicates using source system plus event ID, and quarantines invalid rows with clear reasons. The risk layer calculates transparent signals such as high value, device change, geography, merchant category and short-window velocity. Gold publishes fraud alerts, Customer Risk 360 and hourly monitoring metrics. The default run processes 5,105 physical rows into 5,000 canonical transactions, removes 100 duplicates, quarantines five malformed events, identifies 218 late events and produces 81 explainable alerts while passing the quality gate. The local version is easy to demonstrate with Python and SQLite, and the project includes Kafka, Spark, Databricks, Delta, Airflow, dbt, Snowflake, Terraform, Docker and Kubernetes patterns for enterprise deployment.

## Three-to-five-minute walkthrough

1. Start with the business problem: fraud teams need low-latency transaction visibility, but unreliable events can create false totals, missed cases or duplicated alerts.
2. Explain ingestion: authorization events are keyed by card and published to Kafka; the local demonstration uses equivalent JSONL events.
3. Explain Bronze: raw payloads and broker metadata remain immutable for replay, investigations and schema evolution.
4. Explain Silver: contracts, positive amounts, timestamps and master references are checked; invalid data is quarantined; `(source_system, event_id)` provides deterministic deduplication.
5. Explain event time: late events are measured, and the Spark design uses watermarks and durable checkpoints.
6. Explain risk scoring: rules produce a score and readable reason codes instead of an unexplained result.
7. Explain Gold: alerts support investigators, Customer Risk 360 supports broader risk views, and hourly metrics support operations.
8. Explain quality gates: reject and duplicate rates are compared with configurable limits before data is treated as publishable.
9. Explain governance: Unity Catalog, RBAC, masking, encryption, lineage and audit logs restrict regulated-data access.
10. Explain production operations: CI/CD, Terraform, containers, Kubernetes, SLA monitoring and a replay runbook support reliable deployment and recovery.

## Live demonstration sequence

1. Run `make demo`.
2. Open `data/processed/metrics/quality_report.json` and show the PASS result.
3. Compare the 5,105 physical rows with the 5,000 canonical Silver records.
4. Open `rejected_records.csv` and explain one invalid timestamp or negative amount.
5. Open `risk_scored_transactions.csv` and filter risk scores of 60 or higher.
6. Open `fraud_alerts.csv` and explain the reason codes for one high-severity alert.
7. Open `customer_risk_360.csv` and show how transaction-level data becomes a customer-level product.
8. Run `make test` and explain the end-to-end idempotency test.
9. Show the Spark job and map the local layers to Kafka, Delta tables, checkpoints and Snowflake.

## Data-quality scenario

During a run, the source contains 100 duplicate authorization events and five malformed rows. The pipeline retains every physical record in Bronze, rejects malformed rows with exact reasons, and deduplicates valid events using source system plus event ID. As a result, Silver contains exactly 5,000 canonical transactions. The quality report records a 1.9589 percent duplicate rate and a 0.0979 percent reject rate. Both are within configured limits, so the gate passes.

In production, I would compare the rate with its historical baseline before deciding it is harmless. A sudden duplicate increase could indicate producer retries, a source restart or offset regression. I would inspect producer and broker metadata, correct the cause, replay from Bronze, compare counts and amounts, and promote the corrected version only after control validation.

## Cloud deployment explanation

### AWS and Databricks

- Kafka or Amazon MSK receives card-authorization events; Kinesis is an alternative managed source.
- S3 stores encrypted Bronze, Silver and Gold data.
- Databricks Spark Structured Streaming processes events with checkpoints and Delta Lake ACID tables.
- Unity Catalog manages table ownership, lineage, service principals, row or column restrictions and audited access.
- Airflow or Databricks Workflows coordinates reference-data loads, quality gates and Gold publication.
- Snowflake receives governed marts for investigation, reporting and analytics.
- Terraform provisions storage, catalog, policies, logs and workload identities.
- CloudWatch, Databricks metrics and data-observability checks monitor lag, throughput, failures and freshness.

### Azure alternative

Replace MSK and S3 with Event Hubs and ADLS Gen2. Use Azure Databricks for Delta processing, Key Vault for secrets, Private Link for network isolation, Azure Monitor for platform metrics and Synapse or Snowflake for governed consumption.

## Likely questions and concise answers

### Why did you choose source system plus event ID for deduplication

An event ID may only be unique within one producer. Including the source system prevents unrelated sources from colliding. The key also remains stable across retries and replay, so a rerun produces the same Silver result.

### How do you handle late and out-of-order data

The local pipeline measures the difference between event time and ingestion time. In Spark, I would use event-time processing, a watermark based on the accepted lateness window and checkpointed state. Events later than the normal window would go through a controlled correction path rather than being silently lost.

### How would you reduce false positives

I would monitor alerts by rule, segment and investigator disposition. Thresholds would be versioned and approved. I would add contextual features only when their lineage and freshness were reliable, then use back-testing and champion-challenger evaluation before changing production behavior.

### Why preserve Bronze if Silver is already clean

Bronze is the evidence and recovery boundary. It lets the team replay after a mapping change, investigate a source defect, reconstruct an audit trail and recover from a downstream failure without requesting the source to resend historical events.

### How is the pipeline idempotent

Silver uses a deterministic event key and the local output is rebuilt from Bronze. A production Delta implementation would use checkpointed reads and `MERGE` operations keyed by the same contract. Gold tables would be rebuilt or incrementally merged from a versioned Silver source.

### How would you optimize Spark performance

I would inspect input size, partition distribution, skew, shuffle volume, state-store growth and small files. Likely actions include selecting the correct partition key, controlling shuffle partitions, broadcasting small reference data, compacting Delta files, using optimized writes and avoiding repeated wide transformations. I would validate cost and latency before and after each change.

### How would you secure regulated financial data

I would use least-privilege identities, TLS, encryption at rest, private endpoints, managed secrets, tokenized identifiers, masking, governed catalogs, access reviews, lineage, retention controls and immutable audit logs. Investigator access would differ from analyst access.

### What happens when the quality gate fails

Gold publication stops. I inspect the quality report, group errors by source and reason, compare against the previous run, correct the source or mapping, replay the affected Bronze interval and compare counts and control totals before promotion.

### Why use both Databricks and Snowflake

Databricks is suited to high-volume streaming, stateful processing and Delta lakehouse transformations. Snowflake provides governed SQL consumption for risk, compliance and reporting teams. The boundary keeps compute responsibilities clear and avoids forcing every consumer onto the streaming platform.

### What would you improve next

I would connect the producer to the Spark job in a small cloud environment, add a schema registry, implement Delta `MERGE`, capture Kafka lag and end-to-end latency on a dashboard, and add a feedback table for investigator case outcomes.

## Resume-ready project bullets

- Built a real-time financial fraud and risk lakehouse using Python, PySpark, Kafka, Airflow, Databricks Delta and Snowflake patterns to process card-authorization events into governed fraud alerts and Customer Risk 360 data products.
- Implemented event-contract validation, reference checks, deterministic deduplication, late-event measurement, rejected-record quarantine and configurable quality gates with complete Bronze-to-Gold lineage.
- Developed explainable transaction-risk signals covering value, velocity, device, geography and merchant behavior; the verified demonstration standardized 5,105 physical rows into 5,000 canonical events after removing 100 duplicates and quarantining five malformed records.
- Added automated tests, CI/CD, Terraform, Docker, Kubernetes, dbt models, monitoring guidance and recovery runbooks for secure and repeatable enterprise deployment.

