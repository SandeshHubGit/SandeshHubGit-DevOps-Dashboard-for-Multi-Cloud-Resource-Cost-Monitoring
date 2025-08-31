from sqlalchemy.orm import mapped_column
from sqlalchemy import String, Integer, Float, Date, DateTime, func
from .db import Base

class CostRecord(Base):
    __tablename__ = "cost_records"
    id = mapped_column(Integer, primary_key=True, index=True)
    provider = mapped_column(String(16), index=True)
    account_id = mapped_column(String(64), index=True, nullable=True)
    subscription_id = mapped_column(String(64), index=True, nullable=True)
    project_id = mapped_column(String(128), index=True, nullable=True)
    environment = mapped_column(String(64), index=True, nullable=True)
    service = mapped_column(String(128), index=True, nullable=True)
    usage_amount = mapped_column(Float, nullable=True)
    usage_unit = mapped_column(String(32), nullable=True)
    cost_amount = mapped_column(Float, nullable=False)
    cost_currency = mapped_column(String(8), default="USD")
    date = mapped_column(Date, index=True)

class DailyCost(Base):
    __tablename__ = "daily_costs"
    id = mapped_column(Integer, primary_key=True, index=True)
    provider = mapped_column(String(16), index=True)
    environment = mapped_column(String(64), index=True, nullable=True)
    service = mapped_column(String(128), index=True, nullable=True)
    cost_amount = mapped_column(Float, nullable=False)
    cost_currency = mapped_column(String(8), default="USD")
    date = mapped_column(Date, index=True)

class IngestRun(Base):
    __tablename__ = "ingest_runs"
    id = mapped_column(Integer, primary_key=True, index=True)
    started_at = mapped_column(DateTime(timezone=True), server_default=func.now())
    ended_at = mapped_column(DateTime(timezone=True), nullable=True)
    status = mapped_column(String(16), default="running")
    message = mapped_column(String(512), nullable=True)
