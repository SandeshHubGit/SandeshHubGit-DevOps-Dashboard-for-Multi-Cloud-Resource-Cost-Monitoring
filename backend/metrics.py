import os, datetime as dt
from sqlalchemy import select, func
from prometheus_client import Gauge, CollectorRegistry, generate_latest, CONTENT_TYPE_LATEST
from .db import SessionLocal
from .models import DailyCost

registry = CollectorRegistry()
cost_total_gauge = Gauge("cost_today_total", "Total cost for today by provider", ["provider"], registry=registry)
cost_threshold_gauge = Gauge("cost_threshold", "Configured cost threshold", registry=registry)

def scrape_metrics():
    session = SessionLocal()
    today = dt.date.today()
    try:
        stmt = select(DailyCost.provider, func.sum(DailyCost.cost_amount)).where(DailyCost.date == today).group_by(DailyCost.provider)
        for provider, total in session.execute(stmt).all():
            cost_total_gauge.labels(provider=provider).set(float(total or 0.0))
        threshold = float(os.environ.get("COST_ALERT_THRESHOLD", "100.0"))
        cost_threshold_gauge.set(threshold)
        output = generate_latest(registry)
    finally:
        session.close()
    return output, CONTENT_TYPE_LATEST
