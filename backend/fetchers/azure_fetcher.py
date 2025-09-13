import os
from datetime import datetime, timedelta, timezone
from azure.identity import ClientSecretCredential
from azure.mgmt.costmanagement import CostManagementClient

def fetch_azure_costs():
    """
    Requires:
      AZURE_TENANT_ID
      AZURE_CLIENT_ID
      AZURE_CLIENT_SECRET  (you had AZURE_SECRET; support both)
      AZURE_SUBSCRIPTION_ID
    Returns docs like AWS.
    """
    tenant_id = os.getenv("AZURE_TENANT_ID")
    client_id = os.getenv("AZURE_CLIENT_ID")
    client_secret = os.getenv("AZURE_CLIENT_SECRET") or os.getenv("AZURE_SECRET")
    subscription_id = os.getenv("AZURE_SUBSCRIPTION_ID")

    cred = ClientSecretCredential(tenant_id=tenant_id, client_id=client_id, client_secret=client_secret)
    client = CostManagementClient(credential=cred)

    # Scope at subscription level
    scope = f"/subscriptions/{subscription_id}"

    today = datetime.now(timezone.utc).date()
    start = str(today - timedelta(days=1))
    end = str(today)

    # Azure API expects a definition dict
    query_def = {
        "type": "Usage",
        "timeframe": "Custom",
        "timePeriod": {"from": f"{start}T00:00:00Z", "to": f"{end}T00:00:00Z"},
        "dataset": {
            "granularity": "Daily",
            "aggregation": {
                "totalCost": {
                    "name": "PreTaxCost",
                    "function": "Sum"
                }
            }
        }
    }

    # Depending on SDK version, method is .query(scope, query_def) or .query.usage(scope, query_def)
    response = client.query(scope=scope, parameters=query_def)
    # Response normalization
    amount = 0.0
    currency = "USD"
    rows = getattr(response, "rows", None) or response.get("rows", [])
    col_names = [c.name if hasattr(c, "name") else c.get("name") for c in response.columns]
    # Azure often returns columns like: UsageDate, Currency, PreTaxCost
    try:
        i_date = col_names.index("UsageDate")
    except ValueError:
        i_date = 0
    try:
        i_currency = col_names.index("Currency")
    except ValueError:
        i_currency = None
    try:
        i_cost = col_names.index("PreTaxCost")
    except ValueError:
        i_cost = None

    docs = []
    for r in rows:
        d = str(r[i_date])[:10]
        amt = float(r[i_cost]) if i_cost is not None else 0.0
        cur = r[i_currency] if i_currency is not None else "USD"
        docs.append({"provider": "Azure", "date": d, "amount": amt, "currency": cur})

    return docs

