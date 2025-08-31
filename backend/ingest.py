import os, datetime as dt, argparse
from typing import List, Dict, Any
from sqlalchemy import delete
from sqlalchemy.orm import Session
from apscheduler.schedulers.background import BackgroundScheduler
from .db import SessionLocal, init_db
from .models import CostRecord, DailyCost, IngestRun
from .providers import aws as aws_provider
from .providers import azure as azure_provider
from .providers import gcp as gcp_provider

def upsert_cost_records(session: Session, rows: List[Dict[str, Any]]):
    for r in rows:
        rec = CostRecord(
            provider=r["provider"],
            account_id=r.get("account_id"),
            subscription_id=r.get("subscription_id"),
            project_id=r.get("project_id"),
            environment=r.get("environment"),
            service=r.get("service"),
            usage_amount=r.get("usage_amount"),
            usage_unit=r.get("usage_unit"),
            cost_amount=r.get("cost_amount"),
            cost_currency=r.get("cost_currency", "USD"),
            date=dt.date.fromisoformat(r["date"]),
        )
        session.add(rec)

def rebuild_daily_aggregates(session: Session, date: dt.date):
    session.execute(delete(DailyCost).where(DailyCost.date == date))
    session.execute(
        """
        INSERT INTO daily_costs (provider, environment, service, cost_amount, cost_currency, date)
        SELECT provider, environment, service, SUM(cost_amount) as cost, 'USD' as currency, date
        FROM cost_records
        WHERE date = :date
        GROUP BY provider, environment, service, date
        """,
        {"date": date}
    )

def ingest_once(days: int = 1):
    init_db()
    session = SessionLocal()
    run = IngestRun(status="running", message=f"days={days}")
    session.add(run)
    session.commit()
    try:
        all_rows: List[Dict[str, Any]] = []
        try:
            all_rows += aws_provider.fetch_costs_daily(days=days)
        except Exception as e:
            print("AWS ingest error:", e)
        try:
            if os.environ.get("AZURE_TENANT_ID"):
                all_rows += azure_provider.fetch_costs_daily(days=days)
        except Exception as e:
            print("Azure ingest error:", e)
        try:
            if os.environ.get("GCP_BQ_PROJECT_ID") and os.environ.get("GCP_BQ_TABLE"):
                all_rows += gcp_provider.fetch_costs_daily(days=days)
        except Exception as e:
            print("GCP ingest error:", e)
        if all_rows:
            upsert_cost_records(session, all_rows)
            dates = sorted(set([r["date"] for r in all_rows]))
            for d in dates:
                rebuild_daily_aggregates(session, dt.date.fromisoformat(d))
        run.status = "success"
        run.message = f"rows={len(all_rows)}"
        session.commit()
    except Exception as e:
        run.status = "error"
        run.message = str(e)
        session.commit()
        raise
    finally:
        session.close()

def schedule_ingest():
    scheduler = BackgroundScheduler()
    scheduler.add_job(ingest_once, "interval", minutes=30, id="ingest")
    scheduler.start()
    return scheduler

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--days", type=int, default=1)
    args = parser.parse_args()
    if args.once:
        ingest_once(days=args.days)
    else:
        schedule_ingest()
        import time
        while True:
            time.sleep(3600)
