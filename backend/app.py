import datetime as dt
from fastapi import FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from .db import init_db, SessionLocal, engine
from .schemas import CostResponse, CostRow
from .metrics import scrape_metrics
from .ingest import schedule_ingest

app = FastAPI(title="DevOps Cost Dashboard API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def startup_event():
    init_db()
    schedule_ingest()

@app.get("/api/health")
def health():
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
    return {"status": "ok"}

@app.get("/api/costs", response_model=CostResponse)
def get_costs(provider: str = "all", _from: str = None, to: str = None, group_by: str = "service"):
    session = SessionLocal()
    try:
        if _from:
            from_date = dt.date.fromisoformat(_from)
        else:
            from_date = dt.date.today() - dt.timedelta(days=7)
        to_date = dt.date.fromisoformat(to) if to else dt.date.today()

        where = "WHERE date >= :from_date AND date < :to_date"
        params = {"from_date": from_date, "to_date": to_date}
        if provider != "all":
            where += " AND provider = :provider"
            params["provider"] = provider

        sql = f"""
        SELECT provider, environment, service, date, SUM(cost_amount) as cost, 'USD' as currency
        FROM daily_costs
        {where}
        GROUP BY provider, environment, service, date
        ORDER BY date ASC
        """
        rows = session.execute(text(sql), params).mappings().all()
        payload = [CostRow(provider=r["provider"], environment=r["environment"], service=r["service"],
                           date=r["date"].isoformat(), cost_amount=float(r["cost"]), cost_currency=r["currency"])
                   for r in rows]
        total = sum(r.cost_amount for r in payload)
        return CostResponse(rows=payload, total=total, currency="USD")
    finally:
        session.close()

@app.get("/api/trends", response_model=CostResponse)
def trends(provider: str = "all", window: str = "30d"):
    days = int(window.rstrip("d"))
    session = SessionLocal()
    try:
        from_date = dt.date.today() - dt.timedelta(days=days)
        to_date = dt.date.today()
        where = "WHERE date >= :from_date AND date < :to_date"
        params = {"from_date": from_date, "to_date": to_date}
        if provider != "all":
            where += " AND provider = :provider"
            params["provider"] = provider

        sql = f"""
        SELECT provider, NULL as environment, NULL as service, date, SUM(cost_amount) as cost, 'USD' as currency
        FROM daily_costs
        {where}
        GROUP BY provider, date
        ORDER BY date ASC
        """
        rows = session.execute(text(sql), params).mappings().all()
        payload = [CostRow(provider=r["provider"], environment=None, service=None,
                           date=r["date"].isoformat(), cost_amount=float(r["cost"]), cost_currency=r["currency"])
                   for r in rows]
        total = sum(r.cost_amount for r in payload)
        return CostResponse(rows=payload, total=total, currency="USD")
    finally:
        session.close()

@app.get("/metrics")
def metrics():
    output, ctype = scrape_metrics()
    return Response(content=output, media_type=ctype)
