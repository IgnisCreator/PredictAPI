# Technical decisions

Short records of choices that a reviewer might question. Newest last.

## ADR-001 — Python 3.12 with uv, scikit-learn, FastAPI (PA-01)

uv pins every dependency in `uv.lock` and installs the same environment locally, in CI and in Docker. scikit-learn covers the tabular baseline; PyTorch adds nothing for 1,000 rows. FastAPI generates the OpenAPI/Swagger UI that serves as the only interface.

## ADR-002 — Hash-checked artifacts (PA-02)

`joblib` files are pickles and execute code when loaded. The API loads an artifact only if its SHA-256 matches `models/manifest.json`. A mismatch leaves that version unavailable (503) without stopping the service.

## ADR-003 — Cost-based decision threshold (PA-03)

The dataset defines a 5:1 cost for approving a bad applicant vs. rejecting a good one. At threshold 0.5 both models cost more than rejecting everyone, so each version stores a threshold chosen on out-of-fold train predictions. Details in `docs/model_card.md`.

## ADR-004 — Prediction log fails open (PA-04)

If PostgreSQL is down, `/predict` and `/explain` still answer and return `"logged": false`; the failure is written to the API log. `/ready` stays 200 and reports `"database": "unavailable"`.

- **Why:** this is a demo service where availability matters more than a complete audit trail.
- **Trade-off:** a real credit decision would need fail-closed behaviour (503 when the log write fails), because an unlogged decision cannot be audited. Switching is a one-line change in `record()`.
- **Circuit breaker:** after a failed connection the API stops trying for 30 s. Without it every request waited about 8 s for DNS resolution while the database was down (measured).

## ADR-005 — Migrations as numbered SQL files, applied at startup (PA-04)

`migrations/NNN_*.sql` are applied in order and recorded in `schema_migrations`. A Postgres advisory lock prevents two replicas from migrating at once. No ORM: one table does not justify Alembic/SQLAlchemy.

## ADR-006 — In-memory rate limit (PA-04)

Fixed 1-minute window per client IP, per process (`RATE_LIMIT_PER_MINUTE`, default 60), on `/predict` and `/explain` only. It is exact for one process.

- **Ceiling:** with several replicas each counts separately.
- **Ceiling:** behind a proxy, all clients share the proxy's IP.
- **Upgrade path:** move the limit to the AWS gateway/load balancer or Redis in PA-05.

## ADR-007 — Retention and drift monitoring (PA-04)

- **Retention:** `prediction_log` stores inputs, output, model version, artifact hash and latency. Retention is 180 days. The cleanup is `delete from prediction_log where created_at < now() - interval '180 days'`, indexed by `created_at`; scheduling it belongs to the deployment (PA-05).
- **Drift:** `monitoring/drift_report.py` compares logged inputs against the training split with Evidently's `DataDriftPreset`. It lives in a separate `monitoring` dependency group so the API image does not carry Evidently. Evidently telemetry is disabled with `DO_NOT_TRACK=1`.
