# Verified Demo Results

The default demonstration was executed with Python, seed `20260917`, 500 customers, 750 accounts, 1,000 cards and 5,000 logical transactions.

| Measure | Verified result |
| --- | ---: |
| Physical authorization rows | 5,105 |
| Canonical Silver transactions | 5,000 |
| Rejected malformed rows | 5 |
| Duplicate events removed | 100 |
| Late events observed | 218 |
| Fraud and risk alerts | 81 |
| High-severity alerts | 75 |
| Medium-severity alerts | 6 |
| Customer Risk 360 records | 500 |
| Reject rate | 0.0979% |
| Duplicate rate | 1.9589% |
| Overall quality gate | PASS |
| Automated tests | 4 passed |

## Demonstration evidence

- The physical row count equals 5,000 logical transactions, 100 deliberately duplicated rows and 5 deliberately malformed rows.
- The Silver result returns to exactly 5,000 canonical transactions after validation and deduplication.
- Every invalid row is written to quarantine with its source line and reason.
- Late events remain processable but are measured for operational review.
- Alert rows contain a score, severity and transparent reason codes.
- Re-running the pipeline produces the same canonical and alert counts.

