import os, datetime as dt
from typing import List, Dict, Any
from azure.identity import ClientSecretCredential
from azure.mgmt.costmanagement import CostManagementClient

DEFAULT_ENV_TAG_KEY = os.environ.get("DEFAULT_ENVIRONMENT_TAG_KEY", "Environment")

def fetch_costs_daily(days: int = 1) -> List[Dict[str, Any]]:
    tenant_id = os.environ["AZURE_TENANT_ID"]
    client_id = os.environ["AZURE_CLIENT_ID"]
    client_secret = os.environ["AZURE_CLIENT_SECRET"]
    subscription_id = os.environ["AZURE_SUBSCRIPTION_ID"]
    credential = ClientSecretCredential(tenant_id=tenant_id, client_id=client_id, client_secret=client_secret)
    client = CostManagementClient(credential)
    end_date = dt.date.today()
    start_date = end_date - dt.timedelta(days=days)
    scope = f"/subscriptions/{subscription_id}"
    query = {
        "type": "Usage",
        "timeframe": "Custom",
        "timePeriod": {"from": start_date.isoformat(), "to": end_date.isoformat()},
        "dataset": {
            "granularity": "Daily",
            "aggregation": {
                "totalCost": {"name": "PreTaxCost", "function": "Sum"},
                "totalUsage": {"name": "UsageQuantity", "function": "Sum"},
            },
            "grouping": [
                {"type": "Dimension", "name": "ServiceName"},
                {"type": "Dimension", "name": "SubscriptionId"},
                {"type": "Tag", "name": DEFAULT_ENV_TAG_KEY},
            ],
        },
    }
    response = client.query.usage(scope=scope, parameters=query)
    asdict = response.as_dict()
    cols = [c["name"] for c in asdict.get("columns", [])]
    rows = asdict.get("rows", [])
    def idx(name: str): return cols.index(name) if name in cols else -1
    i_sub = idx("SubscriptionId"); i_serv = idx("ServiceName"); i_cost = idx("PreTaxCost")
    i_usage = idx("UsageQuantity"); i_date = idx("UsageDate"); i_tags = idx("Tags")
    results: List[Dict[str, Any]] = []
    for r in rows:
        subscription = r[i_sub] if i_sub >= 0 else subscription_id
        service = r[i_serv] if i_serv >= 0 else None
        cost = float(r[i_cost]) if i_cost >= 0 and r[i_cost] is not None else 0.0
        usage = float(r[i_usage]) if i_usage >= 0 and r[i_usage] is not None else 0.0
        date = str(r[i_date]) if i_date >= 0 else start_date.isoformat()
        environment = None
        tags_val = r[i_tags] if i_tags >= 0 else None
        if isinstance(tags_val, dict): environment = tags_val.get(DEFAULT_ENV_TAG_KEY) or None
        results.append({
            "provider": "azure",
            "account_id": None,
            "subscription_id": subscription,
            "project_id": None,
            "environment": environment,
            "service": service,
            "usage_amount": usage,
            "usage_unit": "Unit",
            "cost_amount": cost,
            "cost_currency": "USD",
            "date": date,
        })
    return results
