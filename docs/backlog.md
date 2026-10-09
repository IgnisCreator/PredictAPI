# Backlog — PredictAPI

Credit-risk prediction API (German Credit) with per-prediction SHAP explanations.
Source of scope: `portafolio_proyectos.md` (P2) and `plan_implementacion.md` §5 in the planning folder.
A task is **validated** only with evidence in `docs/validation.md`.

States: `pending` · `in progress` · `blocked` · `validated`.

| ID    | Milestone | Exit condition | State |
| ----- | --------- | -------------- | ----- |
| PA-01 | Data + baseline: dataset provenance/hash, stratified split, sklearn pipeline vs. dummy baseline, versioned artifact + manifest | Report with baseline and untouched-test evaluation; test reproduces stored metrics | validated (local) |
| PA-02 | Service: FastAPI `POST /predict`, `GET /health`, `GET /ready`, `GET /models`; Pydantic validation; hash-checked artifact load | Prediction equals offline run; invalid inputs rejected with 422 | pending |
| PA-03 | Explainability: `POST /explain` (SHAP top factors), model card (EN) | Explanation sums to model output; model card lists data, metrics, limits, risks | pending |
| PA-04 | Versions + logs: v1/v2 side by side, PredictionLog in PostgreSQL, rate limiting | Every inference linked to an artifact; DB outage follows documented policy | pending |
| PA-05 | Delivery: multi-stage Dockerfile, GitHub Actions (test → build → push → deploy), AWS deploy, Evidently drift report, README EN/ES | Fresh start with `docker compose up`; CI green; public demo URL | pending |

Out of scope until asked: PyTorch, LIME, own frontend.
