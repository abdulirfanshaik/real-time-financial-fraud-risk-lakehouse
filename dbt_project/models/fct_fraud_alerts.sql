{{ config(materialized='incremental', unique_key='event_id') }}

select
    event_id,
    transaction_id,
    customer_id,
    card_id,
    event_ts,
    amount,
    merchant_category,
    merchant_country,
    risk_score,
    alert_severity,
    current_timestamp() as warehouse_loaded_at
from {{ ref('stg_transactions') }}
where alert_severity in ('MEDIUM', 'HIGH')

{% if is_incremental() %}
  and event_ts > (select coalesce(max(event_ts), '1900-01-01') from {{ this }})
{% endif %}

