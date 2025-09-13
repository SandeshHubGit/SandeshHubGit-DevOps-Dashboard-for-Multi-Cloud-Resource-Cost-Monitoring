# DevOps Dashboard for Multi-Cloud Resource & Cost Monitoring


✨ Features

AWS Cost Ingest via Cost Explorer (backfilled & scheduled)

Provider-agnostic model (provider, amount, date); Azure/GCP are optional and auto-skipped if creds absent

Prometheus metrics for:

cost_today_usd{provider}, cost_mtd_usd{provider}, cost_ytd_usd{provider}, cost_last_year_usd{provider}, cost_total_usd{provider}

doc counts & Mongo collection stats (collStats)

Grafana dashboards: live tiles per provider + trends

Alerting: email (Gmail) when today’s spend > $10

Fully Docker Compose-based

📁 Repository layout
.
├── docker-compose.yml
├── backend/                    # scheduler & fetchers
│   ├── db/mongo_connector.py
│   ├── fetchers/aws_fetcher.py
│   ├── fetchers/azure_fetcher.py         # placeholder (skips if creds missing)
│   ├── fetchers/gcp_fetcher.py           # placeholder (skips if creds missing)
│   └── scheduler/cron_job.py
├── docker/
│   ├── Dockerfile.backend
│   └── cost_exporter/
│       ├── Dockerfile
│       ├── app.py                        # Prom exporter (daily/MTD/YTD/last_year)
│       └── requirements.txt
├── prometheus.yml                        # scrape config + rule_files ref
├── alerting/
│   ├── alert_rules.yml                   # Daily cost alert
│   └── alertmanager.yml                  # Gmail notifier
├── requirements.txt
└── README.md

🔧 Prerequisites

Docker & Docker Compose

AWS IAM user with Cost Explorer access (for now)

Optional: Gmail App Password (for Alertmanager emails)

⚙️ Configuration

Create a .env in the repo root (Compose loads it automatically):

# Mongo (created on first run)
MONGO_INITDB_ROOT_USERNAME=root
MONGO_INITDB_ROOT_PASSWORD=root_password

# Backend connection string to write costs (uses root user)
MONGO_URI=mongodb://root:root_password@mongo:27017/cost_monitoring?authSource=admin

# ---- AWS (required to ingest AWS; leave others blank if not used) ----
AWS_ACCESS_KEY_ID=AKIA...
AWS_SECRET_ACCESS_KEY=...

# ---- Azure (optional; left blank => skipped) ----
AZURE_TENANT_ID=
AZURE_CLIENT_ID=
AZURE_CLIENT_SECRET=
AZURE_SUBSCRIPTION_ID=

# ---- GCP BigQuery (optional; left blank => skipped) ----
GCP_BQ_PROJECT_ID=
GCP_BQ_DATASET=
GCP_BQ_TABLE=

# ---- Cost Exporter ----
COST_EXPORTER_PORT=8000
REFRESH_SECONDS=30


Tip: Only the providers with valid credentials are fetched. Missing creds are safely skipped.

🚀 Quick start

Start the stack

docker compose up -d --build


Services/ports:

MongoDB: 27017

Cost Exporter: 8000 (http://localhost:8000/metrics
)

Prometheus: 9090 (http://localhost:9090
)

Alertmanager: 9093 (http://localhost:9093
)

Grafana: 3000 (http://localhost:3000
)

Create read-only metrics user in Mongo (needed by exporters)

docker exec -it mongo mongosh -u root -p root_password --authenticationDatabase admin <<'EOS'
use admin
if (!db.getUser("metrics")) {
  db.createUser({
    user: "metrics",
    pwd: "metrics_password",
    roles: [
      { role: "clusterMonitor", db: "admin" },
      { role: "read",           db: "admin" },
      { role: "read",           db: "local" },
      { role: "read",           db: "cost_monitoring" }
    ]
  })
} else {
  db.updateUser("metrics", { roles: [
    { role: "clusterMonitor", db: "admin" },
    { role: "read",           db: "admin" },
    { role: "read",           db: "local" },
    { role: "read",           db: "cost_monitoring" }
  ]})
}
use cost_monitoring
db.costs.createIndex({ provider: 1, date: 1 })
EOS


Verify ingestion (backend writes AWS costs every run)

# watch backend logs
docker compose logs -f backend
# show doc count
docker exec -it mongo mongosh -u root -p root_password --authenticationDatabase admin \
  --eval 'db.getSiblingDB("cost_monitoring").costs.countDocuments()'


Verify exporter metrics

# your custom metrics (should show non-zero once docs exist)
curl -s http://localhost:8000/metrics | grep -E '^cost_(today|mtd|ytd|last_year|total)_usd|^cost_docs_total' | sort


Prometheus is scraping

# targets should be "up"
curl -s "http://localhost:9090/api/v1/targets?state=active" | jq '.data.activeTargets[] | {job:.labels.job, health:.health, url:.scrapeUrl}'


In the Prometheus “Query” UI, try:

sum by (provider) (cost_today_usd)

sum by (provider) (cost_mtd_usd)

cost_collstats_total_index_size_bytes

Grafana

Open http://localhost:3000
 (default creds admin/admin) and create panels with queries:

Stat – AWS Today: sum(cost_today_usd{provider="AWS"}) (unit: currency → USD)

Stat – Azure Today: sum(cost_today_usd{provider="Azure"})

Stat – GCP Today: sum(cost_today_usd{provider="GCP"})

Time series (by provider): sum by (provider) (cost_today_usd)

MTD/YTD/Last-year: sum by (provider) (cost_mtd_usd), etc.

Mongo storage/index size: cost_collstats_storage_size_bytes, cost_collstats_total_index_size_bytes (unit: bytes)

If you already have the provided dashboard JSON, import it and select the Prometheus datasource.

🔔 Alerting (email when today > $10)

Alert rule (alerting/alert_rules.yml):

groups:
- name: cost-rules
  rules:
  - alert: DailyCostTooHigh
    expr: sum by (provider) (cost_today_usd) > 10
    for: 5m
    labels:
      severity: warning
    annotations:
      summary: "Daily cost high ({{ $labels.provider }})"
      description: "Today's cost: ${{ printf \"%.2f\" $value }} for {{ $labels.provider }}"


Alertmanager (alerting/alertmanager.yml using Gmail App Password):

global:
  smtp_smarthost: 'smtp.gmail.com:587'
  smtp_from: 'YOUR_GMAIL@gmail.com'
  smtp_auth_username: 'YOUR_GMAIL@gmail.com'
  smtp_auth_password: 'YOUR_16CHAR_APP_PASSWORD'
  smtp_require_tls: true

route:
  receiver: 'gmail'
  group_wait: 30s
  group_interval: 5m
  repeat_interval: 12h

receivers:
- name: 'gmail'
  email_configs:
  - to: 'DESTINATION_EMAIL@example.com'
    send_resolved: true


Reload Prometheus/Alertmanager

docker compose up -d alertmanager prometheus


Check:

Rules: http://localhost:9090/rules

Alerts: http://localhost:9090/alerts

Alertmanager UI: http://localhost:9093

To test quickly, temporarily change the threshold from > 10 to > 0 and wait a couple minutes.

🔍 Useful queries

Per-provider today: sum by (provider) (cost_today_usd)

Total today: sum(cost_today_usd)

MTD/YTD by provider: sum by (provider) (cost_mtd_usd), sum by (provider) (cost_ytd_usd)

Last year by provider: sum by (provider) (cost_last_year_usd)

Docs by provider: sum by (provider) (cost_docs_total)

Mongo sizes: cost_collstats_storage_size_bytes, cost_collstats_total_index_size_bytes

🔐 Security notes

Use Gmail App Password for Alertmanager (not your normal password).

Avoid committing .env with real credentials.

In production, run Mongo with persistent storage & proper auth, and restrict network exposure.

🧪 Health & validation
# Mongo: metrics user can read
docker exec -it mongo mongosh -u metrics -p metrics_password --authenticationDatabase admin \
  --eval 'db.getSiblingDB("cost_monitoring").costs.findOne()'

# Cost Exporter: endpoint is healthy
curl -s http://localhost:8000/metrics | head

# Prometheus: targets up
curl -s "http://localhost:9090/api/v1/targets?state=active" | jq '.data.activeTargets[].health'

🛠️ Troubleshooting
Symptom	Cause	Fix
No data in Grafana	Prometheus not scraping or exporter returning 0	Check http://localhost:9090/targets, ensure cost-exporter is up. curl :8000/metrics should show cost_* gauges.
Prometheus query returns empty	No docs in Mongo yet	Verify ingestion: docker compose logs -f backend and count docs in cost_monitoring.costs.
Authentication failed for metrics	Metrics user missing permissions	Re-run the Create metrics user step (above). Must have read on cost_monitoring + clusterMonitor.
AWS error UnrecognizedClientException	Bad keys or region permissions	Verify AWS_ACCESS_KEY_ID/SECRET_ACCESS_KEY; IAM must allow Cost Explorer GetCostAndUsage.
Alert emails not sent	Gmail auth blocked	Use Gmail App Password, ensure smtp_require_tls: true. See Alertmanager logs.
Mongo collStats zero	Empty collection or permissions	Make sure the metrics user has read on cost_monitoring. Data will be 0 until docs are present.
Azure/GCP “enabled (skipping)”	Placeholders until creds exist	This is expected; only AWS is implemented. Add creds later to enable.

Log inspection

docker compose logs -f backend
docker compose logs -f cost-exporter
docker compose logs -f prometheus
docker compose logs -f alertmanager

🧭 Roadmap

Implement Azure & GCP fetchers (same provider-labelled schema)

Per-service & per-account rollups

Budget thresholds & anomaly detection
