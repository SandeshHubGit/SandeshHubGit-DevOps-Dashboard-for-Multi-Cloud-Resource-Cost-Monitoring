# backend/db/mongo_connector.py
import os
from pymongo import MongoClient, ASCENDING, UpdateOne

MONGO_URI = os.getenv(
    "MONGO_URI",
    "mongodb://root:root_password@mongo:27017/cost_monitoring?authSource=admin",
)
DB_NAME = os.getenv("MONGO_DB", "cost_monitoring")
COLL_NAME = os.getenv("MONGO_COLL", "costs")

_client = MongoClient(MONGO_URI)
_db = _client[DB_NAME]
_coll = _db[COLL_NAME]

def get_db():
    return _db

def get_coll():
    return _coll

def ensure_indexes():
    # unique key keeps re-ingests idempotent (one row per provider/service/date/granularity)
    _coll.create_index(
        [("provider", ASCENDING), ("service", ASCENDING), ("date", ASCENDING), ("granularity", ASCENDING)],
        unique=True,
        name="uniq_provider_service_date_gran",
    )
    _coll.create_index([("provider", ASCENDING), ("date", ASCENDING)], name="provider_date")

def upsert_many(docs):
    if not docs:
        return 0
    ops = []
    for d in docs:
        key = {
            "provider": d.get("provider"),
            "service": d.get("service"),
            "date": d.get("date"),
            "granularity": d.get("granularity", "DAILY"),
        }
        ops.append(UpdateOne(key, {"$set": d}, upsert=True))
    if not ops:
        return 0
    res = _coll.bulk_write(ops, ordered=False)
    # inserted + modified are both progress
    return (res.upserted_count or 0) + (res.modified_count or 0)

