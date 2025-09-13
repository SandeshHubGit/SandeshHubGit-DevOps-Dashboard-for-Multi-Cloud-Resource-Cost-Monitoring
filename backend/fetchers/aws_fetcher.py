# backend/fetchers/aws_fetcher.py
import os
import datetime as dt
from typing import List, Dict

import boto3

def _ce():
    region = os.getenv("AWS_REGION", "us-east-1")
    return boto3.client("ce", region_name=region)

def fetch_daily_costs(days_back: int = 1) -> List[Dict]:
    """
    Returns DAILY UnblendedCost grouped by SERVICE for the last `days_back` days.
    Each item is ready to upsert into Mongo (provider/service/date/granularity).
    """
    if days_back < 1:
        days_back = 1
    end = dt.date.today()
    start = end - dt.timedelta(days=days_back)

    resp = _ce().get_cost_and_usage(
        TimePeriod={"Start": start.isoformat(), "End": end.isoformat()},
        Granularity="DAILY",
        Metrics=["UnblendedCost"],
        GroupBy=[{"Type": "DIMENSION", "Key": "SERVICE"}],
    )

    docs: List[Dict] = []
    for by_time in resp.get("ResultsByTime", []):
        date = dt.datetime.fromisoformat(by_time["TimePeriod"]["Start"])
        for g in by_time.get("Groups", []):
            amount = float(g["Metrics"]["UnblendedCost"]["Amount"])
            unit = g["Metrics"]["UnblendedCost"]["Unit"]
            svc = g["Keys"][0]
            docs.append(
                {
                    "provider": "AWS",
                    "service": svc,
                    "amount": amount,
                    "currency": unit,
                    "date": date,
                    "granularity": "DAILY",
                    "source": "aws-cost-explorer",
                }
            )
    return docs

