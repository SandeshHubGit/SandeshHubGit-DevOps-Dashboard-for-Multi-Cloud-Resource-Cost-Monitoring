import os
import time
import sys

# safety belt in case PYTHONPATH isn't picked up for some reason
sys.path.extend(["/app", "/app/backend"])

from backend.db.mongo_connector import get_db  # must exist
REFRESH = int(os.getenv("REFRESH_SECONDS", "300"))

def tick():
    db = get_db()  # uses MONGO_URI env
    cnt = db["costs"].count_documents({})
    print(f"[backend] costs documents: {cnt}", flush=True)

if __name__ == "__main__":
    print("[backend] scheduler starting…", flush=True)
    while True:
        try:
            tick()
        except Exception as e:
            print(f"[backend] ERROR: {e}", flush=True)
        time.sleep(REFRESH)

