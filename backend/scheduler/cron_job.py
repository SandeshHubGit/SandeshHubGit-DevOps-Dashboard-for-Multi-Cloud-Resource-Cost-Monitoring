# backend/scheduler/cron_job.py
import os
import time
import traceback

from backend.db.mongo_connector import ensure_indexes, upsert_many, get_coll
from backend.fetchers.aws_fetcher import fetch_daily_costs as aws_fetch

# If you later add real fetchers for Azure/GCP, import them here and gate them like AWS.

def aws_enabled() -> bool:
    return bool(os.getenv("AWS_ACCESS_KEY_ID") and os.getenv("AWS_SECRET_ACCESS_KEY"))

def azure_enabled() -> bool:
    # Require all for a real call; if any missing, skip cleanly
    required = ("AZURE_TENANT_ID", "AZURE_CLIENT_ID", "AZURE_CLIENT_SECRET", "AZURE_SUBSCRIPTION_ID")
    return all(os.getenv(k) for k in required)

def gcp_enabled() -> bool:
    # Typical minimal check
    return bool(os.getenv("GOOGLE_APPLICATION_CREDENTIALS"))

def run_aws():
    backfill = int(os.getenv("AWS_BACKFILL_DAYS", "1"))
    docs = aws_fetch(days_back=backfill)
    n = upsert_many(docs)
    print(f"[backend] AWS upserts: {n}", flush=True)

def main():
    print("[backend] scheduler starting...", flush=True)
    ensure_indexes()

    refresh = int(os.getenv("REFRESH_SECONDS", "1800"))  # default 30m

    while True:
        try:
            if aws_enabled():
                try:
                    run_aws()
                except Exception as e:
                    print("[backend] AWS fetch error:", e, flush=True)
                    traceback.print_exc()
            else:
                print("[backend] AWS disabled (credentials missing)", flush=True)

            # Azure
            if azure_enabled():
                print("[backend] Azure enabled (fetcher not implemented here, skipping for now)", flush=True)
            else:
                print("[backend] Azure disabled (credentials missing)", flush=True)

            # GCP
            if gcp_enabled():
                print("[backend] GCP enabled (fetcher not implemented here, skipping for now)", flush=True)
            else:
                print("[backend] GCP disabled (credentials missing)", flush=True)

            try:
                count = get_coll().count_documents({})
                print(f"[backend] costs documents: {count}", flush=True)
            except Exception:
                pass

        except Exception as loop_err:
            print("[backend] loop error:", loop_err, flush=True)
            traceback.print_exc()

        time.sleep(refresh)

if __name__ == "__main__":
    main()

