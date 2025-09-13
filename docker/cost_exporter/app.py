# docker/cost_exporter/app.py
import os
import time
import logging
from http.server import BaseHTTPRequestHandler, HTTPServer

from prometheus_client import CollectorRegistry, Gauge, generate_latest, CONTENT_TYPE_LATEST
from pymongo import MongoClient
from pymongo.errors import PyMongoError

logging.basicConfig(level=logging.INFO, format='[cost-exporter] %(message)s')
LOG = logging.getLogger(__name__)

MONGO_URI = os.getenv(
    "MONGO_URI",
    "mongodb://metrics:metrics_password@mongo:27017/cost_monitoring?authSource=admin&authMechanism=SCRAM-SHA-256",
)
DB_NAME = os.getenv("DB_NAME", "cost_monitoring")
COLL_NAME = os.getenv("COLL_NAME", "costs")
PORT = int(os.getenv("PORT", "8000"))
REFRESH_SECONDS = int(os.getenv("REFRESH_SECONDS", "30"))

_client = None
_last_fetch_ts = 0
_cache = {}


def _mongo():
    global _client
    if _client is None:
        LOG.info(f"Connecting to Mongo: {MONGO_URI}")
        _client = MongoClient(MONGO_URI)
    return _client


def _collect():
    """Fetch fresh numbers from Mongo and return as a dict of simple values."""
    data = {
        "docs_total_all": 0,
        "docs_total_by_provider": {},   # {provider: count}
        "amount_sum_by_provider": {},   # {provider: sum}
        "collstats": {                  # bytes numbers from collStats
            "size": 0,
            "storageSize": 0,
            "totalIndexSize": 0,
        },
    }

    try:
        db = _mongo()[DB_NAME]
        coll = db[COLL_NAME]

        # docs total (all)
        data["docs_total_all"] = coll.count_documents({})

        # docs per provider
        for row in coll.aggregate([
            {"$group": {"_id": "$provider", "c": {"$sum": 1}}},
        ]):
            prov = row["_id"] or "unknown"
            data["docs_total_by_provider"][prov] = int(row["c"])

        # amount sum per provider (sum over *all* docs)
        for row in coll.aggregate([
            {"$match": {"amount": {"$type": "number"}}},
            {"$group": {"_id": "$provider", "sum": {"$sum": "$amount"}}},
        ]):
            prov = row["_id"] or "unknown"
            data["amount_sum_by_provider"][prov] = float(row["sum"])

        # collection stats
        cs = db.command({"collStats": COLL_NAME})
        for k in ("size", "storageSize", "totalIndexSize"):
            data["collstats"][k] = float(cs.get(k, 0))

    except PyMongoError as e:
        LOG.error(f"Mongo error while collecting metrics: {e}")

    return data


def get_metrics():
    """Return Prometheus text for the current snapshot with short caching."""
    global _last_fetch_ts, _cache
    now = time.time()
    if now - _last_fetch_ts > REFRESH_SECONDS or not _cache:
        _cache = _collect()
        _last_fetch_ts = now

    reg = CollectorRegistry()

    # Gauges
    g_docs_all = Gauge("cost_docs_total_all", "Total cost documents (all providers)", registry=reg)
    g_docs = Gauge("cost_docs_total", "Cost documents per provider", ["provider"], registry=reg)
    g_amt  = Gauge("cost_amount_sum", "Total cost amount per provider", ["provider"], registry=reg)

    g_cs_size  = Gauge("cost_collstats_size_bytes", "Collection size (bytes)", registry=reg)
    g_cs_store = Gauge("cost_collstats_storage_size_bytes", "Collection storage size (bytes)", registry=reg)
    g_cs_idx   = Gauge("cost_collstats_total_index_size_bytes", "Collection total index size (bytes)", registry=reg)

    # Fill values
    g_docs_all.set(_cache.get("docs_total_all", 0))

    for prov, cnt in _cache.get("docs_total_by_provider", {}).items():
        g_docs.labels(provider=prov).set(cnt)

    for prov, s in _cache.get("amount_sum_by_provider", {}).items():
        g_amt.labels(provider=prov).set(s)

    cs = _cache.get("collstats", {})
    g_cs_size.set(cs.get("size", 0))
    g_cs_store.set(cs.get("storageSize", 0))
    g_cs_idx.set(cs.get("totalIndexSize", 0))

    return generate_latest(reg)


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path != "/metrics":
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b"not found")
            return
        try:
            output = get_metrics()
            self.send_response(200)
            self.send_header("Content-Type", CONTENT_TYPE_LATEST)
            self.end_headers()
            self.wfile.write(output)
        except Exception as e:  # noqa
            LOG.error(f"/metrics failed: {e}")
            self.send_response(500)
            self.end_headers()
            self.wfile.write(b"error")


if __name__ == "__main__":
    LOG.info(f"Starting cost-exporter on :{PORT} using DB={DB_NAME} coll={COLL_NAME}")
    httpd = HTTPServer(("0.0.0.0", PORT), Handler)
    httpd.serve_forever()

