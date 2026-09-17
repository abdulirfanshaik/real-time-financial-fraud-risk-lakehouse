create schema if not exists financial_risk.silver;
create schema if not exists financial_risk.gold;

create or replace table financial_risk.silver.card_transactions (
    event_id varchar not null,
    transaction_id varchar not null,
    customer_id varchar not null,
    account_id varchar not null,
    card_id varchar not null,
    event_ts timestamp_tz not null,
    ingest_ts timestamp_tz not null,
    amount number(18, 2) not null,
    currency varchar(3) not null,
    merchant_id varchar not null,
    merchant_category varchar not null,
    merchant_country varchar not null,
    customer_country varchar not null,
    device_id varchar not null,
    channel varchar not null,
    decision varchar not null,
    customer_risk_tier varchar,
    risk_score integer,
    alert_severity varchar,
    source_system varchar not null,
    source_file varchar,
    source_line_number integer,
    constraint uq_card_event unique (source_system, event_id)
);

create or replace table financial_risk.gold.fraud_alerts (
    alert_id varchar not null,
    event_id varchar not null,
    transaction_id varchar not null,
    customer_id varchar not null,
    card_id varchar not null,
    event_ts timestamp_tz not null,
    amount number(18, 2) not null,
    risk_score integer not null,
    severity varchar not null,
    reasons varchar,
    case_status varchar not null,
    created_at timestamp_tz default current_timestamp(),
    constraint pk_fraud_alert primary key (alert_id)
);

create or replace masking policy financial_risk.public.mask_customer_identifier
as (value varchar) returns varchar ->
  case
    when current_role() in ('FRAUD_INVESTIGATOR', 'DATA_STEWARD') then value
    else concat('***', right(value, 4))
  end;

