# Data Dictionary

## Raw source files

### customers.csv

| Field | Type | Description |
| --- | --- | --- |
| customer_id | string | Stable synthetic customer identifier |
| country | string | Customer home country code |
| risk_tier | string | LOW, MEDIUM or HIGH demonstration risk tier |
| kyc_status | string | VERIFIED or REVIEW |
| segment | string | MASS, AFFLUENT or SMALL_BUSINESS |

### accounts.csv

| Field | Type | Description |
| --- | --- | --- |
| account_id | string | Stable synthetic account identifier |
| customer_id | string | Owning customer |
| account_type | string | CHECKING, SAVINGS or CREDIT |
| status | string | Account status |
| opened_date | date | Representative open date |

### cards.csv

| Field | Type | Description |
| --- | --- | --- |
| card_id | string | Tokenized synthetic card identifier |
| account_id | string | Linked account |
| customer_id | string | Linked customer |
| card_type | string | DEBIT or CREDIT |
| primary_device_id | string | Known device used for comparison |
| status | string | Card status |

### card_authorizations.jsonl

| Field | Type | Description |
| --- | --- | --- |
| event_id | string | Event-level idempotency identifier |
| transaction_id | string | Business transaction identifier |
| customer_id | string | Customer reference |
| account_id | string | Account reference |
| card_id | string | Tokenized card reference |
| event_ts | timestamp | Authorization event time in UTC |
| ingest_ts | timestamp | Platform ingestion time in UTC |
| amount | decimal | Authorization amount |
| currency | string | ISO-style currency code |
| merchant_id | string | Synthetic merchant identifier |
| merchant_category | string | Merchant category used by risk rules |
| merchant_country | string | Merchant country or fictional HRC demonstration code |
| customer_country | string | Customer country copied for transparent comparison |
| device_id | string | Device involved in the authorization |
| channel | string | CARD_PRESENT, ECOMMERCE or MOBILE_WALLET |
| decision | string | APPROVED or DECLINED |
| source_system | string | Originating source-system name |

## Silver fields added by processing

| Field | Description |
| --- | --- |
| customer_risk_tier | Enrichment from the customer master |
| is_late_event | 1 when ingest time is more than 15 minutes after event time |
| source_file | Input filename for lineage |
| source_line_number | Source line for issue investigation |

## Gold risk fields

| Field | Description |
| --- | --- |
| velocity_count_10m | Number of events for the card in the prior 10-minute window |
| risk_score | Explainable score capped at 100 |
| risk_reasons | Pipe-delimited rule reason codes |
| alert_severity | NONE, MEDIUM or HIGH |
| case_status | Initial fraud-review state, OPEN in the demonstration |

