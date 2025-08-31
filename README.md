
# DevOps Dashboard for Multi‑Cloud Resource & Cost Monitoring

![Sample Screenshot](screenshots/devops_dashboard_sample.png)

> Centralized, Dockerized observability stack to **collect**, **store**, **visualize**, and **alert** on resource usage and costs across **AWS**, **Azure**, and **GCP** — with **Grafana** for dashboards and **Prometheus/Alertmanager** for alerting (MS Teams notifications supported). Data is persisted in **MongoDB**; data collectors are implemented in **Python** (manual, step‑by‑step—no magic automation).

---

## ✨ Features

- **Cloud coverage:** AWS, Azure, GCP — costs + basic resource KPIs (CPU, memory, instance counts).
- **Manual, explicit steps:** Clear API setup + credentials, Python collectors, and schedules.
- **Data store:** MongoDB (simple, queryable schema).
- **Dashboards:** Grafana (pre‑built panels; provisioning examples included).
- **Alerting:** Prometheus rules → Alertmanager → MS Teams (via bridge container).
- **Deployment:** Single `docker-compose` for local or server use.
- **Extensible:** Add new collectors or exporters without changing the core stack.

---

## 🏗️ Architecture

```
+---------------------------+
|        Frontend           |
|        Grafana            |
+------------+--------------+
             |
             v
+------------+--------------+      +----------------------------+
|        Prometheus         | <----| Exporters / /metrics       |
| (scrapes app/exporter     |      | (optional: node/app stats) |
|  endpoints, evaluates     |      +----------------------------+
|  alert rules)             |
+------------+--------------+
             |
             v
+---------------------------+
|      Alertmanager         |--- MS Teams (webhook via bridge)
+---------------------------+
             ^
             |
+------------+--------------+
|    Python Data Collectors |
|  (AWS/Azure/GCP APIs)     |
|    -> MongoDB             |
+------------+--------------+
             |
             v
+---------------------------+
|          MongoDB          |
|  (costs, usage, alerts)   |
+---------------------------+
```

---

## 📁 Repository Structure

```
.
├─ collectors/
│  ├─ aws_costs.py
│  ├─ azure_costs.py
│  ├─ gcp_costs.py
│  ├─ usage_aggregator.py
│  └─ common/
│     ├─ db.py
│     └─ utils.py
├─ grafana/
│  ├─ dashboards/
│  │  └─ devops-dashboard.json
│  └─ provisioning/
│     ├─ dashboards.yml
│     └─ datasources.yml
├─ prometheus/
│  ├─ prometheus.yml
│  └─ rules.yml
├─ alertmanager/
│  └─ alertmanager.yml
├─ docker-compose.yml
├─ .env.example
└─ README.md
```

---

## ✅ Prerequisites

- **Docker & Docker Compose**
- **Accounts & credentials** for:
  - AWS: Cost Explorer + CloudWatch permissions
  - Azure: Cost Management + Monitor (Service Principal)
  - GCP: Cloud Billing Export + Monitoring (Service Account)
- **MongoDB** (container provided)
- **MS Teams Incoming Webhook** in a channel (Connector)

> *All credentials are provided via `.env` (see below). Never commit secrets.*

---

## ⚙️ Configuration

Copy the example env and fill values:

```bash
cp .env.example .env
```

`.env.example`

```dotenv
# Mongo
MONGO_URI=mongodb://mongo:27017
MONGO_DB=devops_dashboard

# AWS (Cost Explorer, CloudWatch)
AWS_ACCESS_KEY_ID=
AWS_SECRET_ACCESS_KEY=
AWS_DEFAULT_REGION=us-east-1
AWS_LINKED_ACCOUNT_IDS=acct1,acct2

# Azure (Service Principal)
AZURE_TENANT_ID=
AZURE_CLIENT_ID=
AZURE_CLIENT_SECRET=
AZURE_SUBSCRIPTION_IDS=sub1,sub2
AZURE_COST_SCOPE=/subscriptions/<sub_id>

# GCP (Service Account JSON mounted at ./gcp-key.json)
GCP_PROJECT_IDS=proj1,proj2
GCP_BILLING_ACCOUNT=XXXX-XXXX-XXXX
GCP_APPLICATION_CREDENTIALS=/run/secrets/gcp_key

# Prometheus/Alerting
ALERT_COST_BUDGET_USD=2000
ALERT_CPU_UTIL_THRESHOLD=80

# MS Teams
MSTEAMS_WEBHOOK_URL=https://outlook.office.com/webhook/...
```

---

## 🗃️ MongoDB Schema (minimal)

- **`cloud_costs`**
  ```json
  {
    "provider": "aws|azure|gcp",
    "account": "string",
    "service": "EC2|S3|ComputeEngine|...",
    "date": "YYYY-MM-DD",
    "currency": "USD",
    "amount": 123.45,
    "tags": {"env":"prod","team":"platform"}
  }
  ```

- **`resource_usage`**
  ```json
  {
    "provider":"aws|azure|gcp",
    "resource_id":"string",
    "metric":"cpu|memory|count",
    "value": 63.2,
    "unit":"%",
    "timestamp":"ISO-8601",
    "labels":{"tier":"api","region":"us-east-1"}
  }
  ```

---

## 🐍 Python Collectors (manual runs)

Each collector authenticates to its cloud API, pulls cost/usage, and **inserts documents into MongoDB**.

Example: `collectors/aws_costs.py`
```python
#!/usr/bin/env python3
import os, datetime, boto3
from decimal import Decimal
from pymongo import MongoClient

mongo = MongoClient(os.environ["MONGO_URI"])
db = mongo[os.environ.get("MONGO_DB", "devops_dashboard")]

ce = boto3.client("ce", region_name=os.environ.get("AWS_DEFAULT_REGION", "us-east-1"))

def upsert_costs(start, end):
    resp = ce.get_cost_and_usage(
        TimePeriod={"Start": start, "End": end},
        Granularity="DAILY",
        Metrics=["UnblendedCost"],
        GroupBy=[{"Type":"DIMENSION","Key":"SERVICE"}]
    )
    for day in resp["ResultsByTime"]:
        for group in day.get("Groups", []):
            amount = Decimal(group["Metrics"]["UnblendedCost"]["Amount"])
            doc = {
                "provider":"aws",
                "account":"master",
                "service":group["Keys"][0],
                "date":day["TimePeriod"]["Start"],
                "currency":"USD",
                "amount":float(amount)
            }
            db.cloud_costs.update_one(
                {"provider":"aws","service":doc["service"],"date":doc["date"]},
                {"$set":doc},
                upsert=True
            )

if __name__ == "__main__":
    end = datetime.date.today()
    start = (end - datetime.timedelta(days=7))
    upsert_costs(start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d"))
```

> Similar collectors exist for Azure (Cost Management Query) and GCP (Cloud Billing BigQuery export or Billing API).

---

## 📊 Grafana

- Provisioned via files in `grafana/provisioning` (datasource: Prometheus for live metrics; Mongo via plugin if desired).
- Import `grafana/dashboards/devops-dashboard.json` for a ready dashboard including:
  - Total monthly spend, per‑provider spend, cost trends
  - Resource KPIs (avg CPU per tier, instance counts)
  - Alerts panel (from Alertmanager)

**Datasource provisioning (example):**
```yaml
# grafana/provisioning/datasources.yml
apiVersion: 1
datasources:
  - name: Prometheus
    type: prometheus
    access: proxy
    url: http://prometheus:9090
    isDefault: true
```

---

## ⏱️ Prometheus & Alerts

`prometheus/prometheus.yml`
```yaml
global:
  scrape_interval: 30s

scrape_configs:
  - job_name: "prometheus"
    static_configs:
      - targets: ["prometheus:9090"]
  # Add exporters here (node, custom app metrics, etc.)
rule_files:
  - /etc/prometheus/rules.yml
```

`prometheus/rules.yml`
```yaml
groups:
- name: cost-and-utilization
  rules:
  - alert: MonthlyBudgetExceeded
    expr: (sum_over_time(cloud_cost_usd_total[30d])) > 2000
    for: 5m
    labels:
      severity: warning
    annotations:
      summary: "Cloud costs over budget"
      description: "30‑day rolling cost exceeded budget."
  - alert: HighCPU
    expr: avg by (tier) (app_cpu_utilization_percent) > 80
    for: 10m
    labels:
      severity: critical
    annotations:
      summary: "High CPU on {{ $labels.tier }}"
      description: "CPU > threshold for 10m."
```

---

## 📣 Alertmanager → MS Teams

> Alertmanager does not post to Teams natively. Use the **prometheus-msteams** bridge.

`alertmanager/alertmanager.yml`
```yaml
route:
  receiver: "msteams"
receivers:
  - name: "msteams"
    webhook_configs:
      - url: "http://prometheus-msteams:2000/alertmanager"  # bridge
```

**Bridge container env:**
- `MSTEAMS_INCOMING_WEBHOOK_URL` = your Teams channel webhook

---

## 🐳 Docker Compose

`docker-compose.yml`
```yaml
version: "3.9"

services:
  mongo:
    image: mongo:7
    restart: unless-stopped
    volumes:
      - mongo_data:/data/db
    ports: ["27017:27017"]

  prometheus:
    image: prom/prometheus:v2.54.1
    restart: unless-stopped
    volumes:
      - ./prometheus/prometheus.yml:/etc/prometheus/prometheus.yml:ro
      - ./prometheus/rules.yml:/etc/prometheus/rules.yml:ro
    ports: ["9090:9090"]

  alertmanager:
    image: prom/alertmanager:v0.27.0
    restart: unless-stopped
    volumes:
      - ./alertmanager/alertmanager.yml:/etc/alertmanager/alertmanager.yml:ro
    ports: ["9093:9093"]
    depends_on: ["prometheus"]

  prometheus-msteams:
    image: quay.io/prometheusmsteams/prometheus-msteams:v1.6.0
    restart: unless-stopped
    environment:
      - MSTEAMS_INCOMING_WEBHOOK_URL=${MSTEAMS_WEBHOOK_URL}
    ports: ["2000:2000"]
    depends_on: ["alertmanager"]

  grafana:
    image: grafana/grafana:11.1.0
    restart: unless-stopped
    ports: ["3000:3000"]
    volumes:
      - ./grafana/provisioning:/etc/grafana/provisioning:ro

  collectors:
    build:
      context: .
      dockerfile: Dockerfile.collectors
    environment:
      - MONGO_URI=${MONGO_URI}
      - MONGO_DB=${MONGO_DB}
      - AWS_ACCESS_KEY_ID=${AWS_ACCESS_KEY_ID}
      - AWS_SECRET_ACCESS_KEY=${AWS_SECRET_ACCESS_KEY}
      - AWS_DEFAULT_REGION=${AWS_DEFAULT_REGION}
      - AZURE_TENANT_ID=${AZURE_TENANT_ID}
      - AZURE_CLIENT_ID=${AZURE_CLIENT_ID}
      - AZURE_CLIENT_SECRET=${AZURE_CLIENT_SECRET}
      - AZURE_SUBSCRIPTION_IDS=${AZURE_SUBSCRIPTION_IDS}
      - GCP_PROJECT_IDS=${GCP_PROJECT_IDS}
      - GCP_BILLING_ACCOUNT=${GCP_BILLING_ACCOUNT}
    secrets:
      - gcp_key
    depends_on: ["mongo"]

secrets:
  gcp_key:
    file: ./gcp-key.json

volumes:
  mongo_data:
```

> Build the collectors image with a `Dockerfile.collectors` that installs: `python:3.11-slim` + `boto3`, `azure-identity`, `azure-mgmt-costmanagement`, `google-cloud-billing`/`bigquery`, `pymongo`, `schedule` or `cron`.

---

## 🚀 Quickstart

```bash
# 1) Configure secrets
cp .env.example .env
# edit .env with your credentials

# 2) (Optional) Place GCP key as gcp-key.json

# 3) Start the stack
docker compose up -d

# 4) Run collectors manually inside the container (or use cron)
docker compose exec collectors python collectors/aws_costs.py
docker compose exec collectors python collectors/azure_costs.py
docker compose exec collectors python collectors/gcp_costs.py

# 5) Open Grafana
# http://localhost:3000  (admin / admin on first run)
```

---

## 🔒 Security & Production Notes

- Store secrets in `.env` / Docker secrets; **never** commit them.
- Restrict IAM to **read‑only** cost/monitoring APIs.
- Add TLS (reverse proxy like Nginx/Caddy) and SSO (OAuth proxy) for Grafana.
- Back up MongoDB volume regularly.
- Use exporters (Node Exporter, cAdvisor) for deeper utilization metrics.

---

## 🧪 Troubleshooting

- **Grafana cannot see Prometheus** → check datasource URL `http://prometheus:9090`.
- **No data in dashboards** → run collectors; confirm MongoDB has documents.
- **MS Teams alerts not arriving** → verify `prometheus-msteams` logs and webhook URL.
- **Permission errors** → verify cloud roles: AWS Cost Explorer, Azure CostManagement Reader, GCP Billing Viewer.

---

## 🗺️ Roadmap

- Add FinOps KPIs (RI/Savings Plan coverage, rightsizing suggestions).
- Add automated schedule for collectors (cron).
- Add per‑team/showback tagging breakdowns.
- Add Terraform to deploy the stack.

---

## 📜 License

MIT
