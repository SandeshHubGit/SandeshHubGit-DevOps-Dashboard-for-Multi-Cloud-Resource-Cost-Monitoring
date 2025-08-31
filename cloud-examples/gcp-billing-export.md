# GCP Billing Export to BigQuery (high level)

1. In Cloud Console, enable Billing Export to BigQuery (Detailed usage cost table).
2. Create a service account with BigQuery Data Viewer on the dataset.
3. Download key JSON and mount into container as ./gcp-key.json
4. Set env: GCP_BQ_PROJECT_ID, GCP_BQ_DATASET, GCP_BQ_TABLE
