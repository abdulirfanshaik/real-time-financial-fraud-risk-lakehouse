from __future__ import annotations

from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.bash import BashOperator


default_args = {
    "owner": "financial-risk-data-engineering",
    "depends_on_past": False,
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
}

with DAG(
    dag_id="financial_fraud_risk_lakehouse",
    description="Generate, process, validate and publish fraud-risk data products",
    default_args=default_args,
    schedule="0 * * * *",
    start_date=datetime(2026, 1, 1),
    catchup=False,
    max_active_runs=1,
    tags=["financial-services", "fraud", "risk", "lakehouse"],
) as dag:
    generate = BashOperator(
        task_id="generate_representative_events",
        bash_command="PYTHONPATH=src python -m risk_lakehouse.generator --output data/raw",
    )
    process = BashOperator(
        task_id="process_bronze_silver_gold",
        bash_command="PYTHONPATH=src python -m risk_lakehouse.pipeline --input data/raw --output data/processed --config config/project.json",
    )
    dbt_test = BashOperator(
        task_id="validate_warehouse_models",
        bash_command="cd dbt_project && dbt test --profiles-dir .",
    )
    publish_metrics = BashOperator(
        task_id="publish_quality_metrics",
        bash_command="python -c \"import json; print(json.load(open('data/processed/metrics/quality_report.json')))\"",
    )

    generate >> process >> dbt_test >> publish_metrics

