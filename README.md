
# DevOps Dashboard — Multi‑Cloud Resource & Cost Monitoring

Containerized, end‑to‑end dashboard aggregating **AWS**, **Azure**, **GCP** costs into **PostgreSQL**, exposing **FastAPI** endpoints and **Prometheus** metrics, visualized in **Grafana**, with alerts via **Prometheus + Alertmanager**.

## Quickstart

```bash
cp .env.example .env
# edit .env with your credentials
docker compose up -d --build
```

- API: http://localhost:8000/docs
- Grafana: http://localhost:3000 (admin / admin)
- Prometheus: http://localhost:9090
- Alertmanager: http://localhost:9093
