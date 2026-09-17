-- Alert volume and risk by hour.
select
    date_trunc('hour', event_ts) as event_hour,
    severity,
    count(*) as alert_count,
    round(avg(risk_score), 2) as average_risk_score,
    sum(amount) as alerted_amount
from financial_risk.gold.fraud_alerts
group by 1, 2
order by 1, 2;

-- Customers requiring priority review.
select
    customer_id,
    count(*) as alert_count,
    max(risk_score) as maximum_risk_score,
    sum(amount) as total_alerted_amount
from financial_risk.gold.fraud_alerts
where case_status = 'OPEN'
group by customer_id
having count(*) >= 2 or max(risk_score) >= 90
order by maximum_risk_score desc, alert_count desc;

-- Control query: no duplicate canonical events.
select source_system, event_id, count(*) as row_count
from financial_risk.silver.card_transactions
group by source_system, event_id
having count(*) > 1;

