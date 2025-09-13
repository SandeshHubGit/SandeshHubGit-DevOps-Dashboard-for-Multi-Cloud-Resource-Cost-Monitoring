import os
from datetime import datetime, timedelta, timezone
from google.cloud import bigquery

def fetch_gcp_costs():
    """
    Requires:
      GCP_BQ_PROJECT_ID
      GCP_BQ_DATASET
      GCP_BQ_TABLE              (full table name without project)
      GOOGLE_APPLICATION_CREDENTIALS (path to JSON in container)
    Returns docs like AWS.
    """
    project = os.getenv("GCP_BQ_PROJECT_ID")
    dataset = os.getenv("GCP_BQ_DATASET")
    table = os.getenv("GCP_BQ_TABLE")  # e.g., gcp_billing_export_v1_XXXXXX

    client = bigquery.Client(project=project)

    # Yesterday UTC
    day = (datetime.now(timezone.utc).date() - timedelta(days=1)).isoformat()

    query = f"""
    SELECT
      DATE(usage_start_time) AS day,
      SUM(cost) AS amount,
      ANY_VALUE(currency) AS currency
    FROM `{project}.{dataset}.{table}`
    WHERE DATE(usage_start_time) = @day
    GROUP BY day
    """
    job_config = bigquery.QueryJobConfig(
        query_parameters=[bigquery.ScalarQueryParameter("day", "DATE", day)]
    )
    rows = client.query(query, job_config=job_config).result()
    docs = []
    for row in rows:
        docs.append({
            "provider": "GCP",
            "date": row["day"].isoformat(),
            "amount": float(row["amount"] or 0.0),
            "currency": row["currency"] or "USD"
        })
    # If no rows, still return 0-cost row to make panels show
    if not docs:
        docs.append({"provider": "GCP", "date": day, "amount": 0.0, "currency": "USD"})
    return docs

