#!/usr/bin/env bash
set -euo pipefail
docker compose exec backend python -m backend.ingest --once --days "${1:-1}"
