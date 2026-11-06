"""PostgreSQL access: versioned SQL migrations and the prediction log.

Without DATABASE_URL the API still serves predictions and reports `logged: false` (see docs/decisions.md).
"""

import logging
import os
import time
from pathlib import Path

import psycopg
from psycopg.types.json import Jsonb

MIGRATIONS = Path(__file__).resolve().parent.parent / "migrations"
log = logging.getLogger("predictapi.db")


COOLDOWN_S = 30
down_until = 0.0


def connect():
    """Open a connection; after a failure, fail fast for COOLDOWN_S instead of waiting on every request."""
    global down_until
    if time.monotonic() < down_until:
        raise psycopg.OperationalError("database marked unavailable, waiting for cooldown")
    try:
        # ponytail: una conexión por petición; usar psycopg_pool si el throughput lo exige
        return psycopg.connect(os.environ["DATABASE_URL"], connect_timeout=2)
    except psycopg.OperationalError:
        # Sin esto, cada petición espera la resolución DNS/timeout (~8 s medidos) mientras la base está caída
        down_until = time.monotonic() + COOLDOWN_S
        raise


def migrate():
    """Apply migrations/*.sql in name order, each exactly once."""
    with connect() as conn:
        conn.execute("select pg_advisory_xact_lock(4242)")  # dos réplicas no migran a la vez
        conn.execute(
            "create table if not exists schema_migrations "
            "(version text primary key, applied_at timestamptz not null default now())"
        )
        applied = {row[0] for row in conn.execute("select version from schema_migrations")}
        for path in sorted(MIGRATIONS.glob("*.sql")):
            if path.name not in applied:
                conn.execute(path.read_text())
                conn.execute("insert into schema_migrations (version) values (%s)", (path.name,))


def log_prediction(row):
    """Insert one prediction; return False instead of raising when the database is unavailable."""
    if not os.environ.get("DATABASE_URL"):
        return False
    try:
        with connect() as conn:
            conn.execute(
                "insert into prediction_log (request_id, endpoint, model_version, model_sha256, features,"
                " probability_bad, threshold, prediction, latency_ms) values (%(request_id)s, %(endpoint)s,"
                " %(model_version)s, %(model_sha256)s, %(features)s, %(probability_bad)s, %(threshold)s,"
                " %(prediction)s, %(latency_ms)s)",
                {**row, "features": Jsonb(row["features"])},
            )
        return True
    except psycopg.Error as exc:
        log.warning("prediction %s not logged: %s", row["request_id"], exc)
        return False


def status():
    if not os.environ.get("DATABASE_URL"):
        return "disabled"
    try:
        with connect() as conn:
            conn.execute("select 1")
        return "ok"
    except psycopg.Error:
        return "unavailable"
