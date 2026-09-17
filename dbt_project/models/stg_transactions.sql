select
    event_id,
    transaction_id,
    customer_id,
    account_id,
    card_id,
    cast(event_ts as timestamp) as event_ts,
    cast(amount as decimal(18, 2)) as amount,
    currency,
    merchant_id,
    merchant_category,
    merchant_country,
    customer_country,
    device_id,
    channel,
    decision,
    customer_risk_tier,
    cast(risk_score as integer) as risk_score,
    alert_severity
from {{ source('lakehouse', 'card_transactions') }}

