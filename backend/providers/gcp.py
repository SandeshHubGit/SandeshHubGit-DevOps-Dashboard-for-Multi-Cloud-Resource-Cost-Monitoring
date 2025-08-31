import os, datetime as dt
from typing import List, Dict, Any
from google.cloud import bigquery

def fetch_costs_daily(days: int = 1) -> List[Dict[str, Any]]:
    project_id = os.environ.get("GCP_BQ_PROJECT_ID")
    dataset = os.environ.get("GCP_BQ_DATASET", "billing_export")
    table = os.environ.get("GCP_BQ_TABLE")
    currency = os.environ.get("GCP_BILLING_CURRENCY", "USD")
    client = bigquery.Client(project=project_id)
    end_date = dt.date.today()
    start_date = end_date - dt.timedelta(days=days)
    query = f"""
    SELECT
      DATE(usage_start_time) as date,
      project.id as project_id,
      service.description as service,
      SUM(cost) as cost_amount,
      SUM(IFNULL(usage.amount, 0)) as usage_amount,
      ANY_VALUE(currency) as currency
    FROM `{project_id}.{dataset}.{table}`
    WHERE DATE(usage_start_time) >= @start AND DATE(usage_start_time) < @end
    GROUP BY 1,2,3
    ORDER BY 1
    """
    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("start", "DATE", start_date),
            bigquery.ScalarQueryParameter("end", "DATE", end_date),
        ]
    )
    rows = client.query(query, job_config=job_config).result()
    results: List[Dict[str, Any]] = []
    for row in rows:
        results.append({
            "provider": "gcp",
            "account_id": None,
            "subscription_id": None,
            "project_id": row.project_id,
            "environment": None,
            "service": row.service,
            "usage_amount": float(row.usage_amount or 0.0),
            "usage_unit": "Unit",
            "cost_amount": float(row.cost_amount or 0.0),
            "cost_currency": row.currency or currency,
            "date": row.date.isoformat(),
        })
    return results
