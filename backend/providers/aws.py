import os, datetime as dt
from typing import List, Dict, Any, Optional
import boto3

DEFAULT_ENV_TAG_KEY = os.environ.get("DEFAULT_ENVIRONMENT_TAG_KEY", "Environment")

def _date_range(days: int = 1):
    end = dt.date.today()
    start = end - dt.timedelta(days=days)
    return start.isoformat(), end.isoformat()

def fetch_costs_daily(days: int = 1) -> List[Dict[str, Any]]:
    region = os.environ.get("AWS_REGION", "us-east-1")
    ce = boto3.client("ce", region_name=region)
    start, end = _date_range(days)
    results = []
    group_defs = [{"Type": "DIMENSION", "Key": "SERVICE"}]
    group_defs.append({"Type": "DIMENSION", "Key": "LINKED_ACCOUNT"})
    try:
        group_defs.append({"Type": "TAG", "Key": f"{DEFAULT_ENV_TAG_KEY}"})
    except Exception:
        pass
    token: Optional[str] = None
    while True:
        resp = ce.get_cost_and_usage(
            TimePeriod={"Start": start, "End": end},
            Granularity="DAILY",
            Metrics=["UnblendedCost", "UsageQuantity"],
            GroupBy=group_defs,
            NextPageToken=token
        )
        for period in resp.get("ResultsByTime", []):
            date = period["TimePeriod"]["Start"]
            for group in period.get("Groups", []):
                keys = group.get("Keys", [])
                service = keys[0] if len(keys) > 0 else None
                account_id = keys[1] if len(keys) > 1 else None
                environment = None
                if len(keys) > 2:
                    tag_val = keys[2]
                    if "$" in tag_val:
                        environment = tag_val.split("$", 1)[1]
                amount = float(group["Metrics"]["UnblendedCost"]["Amount"] or 0.0)
                usage = float(group["Metrics"]["UsageQuantity"]["Amount"] or 0.0)
                results.append({
                    "provider": "aws",
                    "account_id": account_id,
                    "subscription_id": None,
                    "project_id": None,
                    "environment": environment,
                    "service": service,
                    "usage_amount": usage,
                    "usage_unit": "Unit",
                    "cost_amount": amount,
                    "cost_currency": "USD",
                    "date": date,
                })
        token = resp.get("NextPageToken")
        if not token:
            break
    return results
