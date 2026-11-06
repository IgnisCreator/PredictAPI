# Backlog — PredictAPI

Credit-risk prediction API (German Credit) with per-prediction SHAP explanations.
Source of scope: `portafolio_proyectos.md` (P2) and `plan_implementacion.md` §5 in the planning folder.
A task is **validated** only with evidence in `docs/validation.md`.

States: `pending` · `in progress` · `blocked` · `validated`.

Each milestone groups work that shares the same dependency: a milestone never needs something built in a later one.

| ID    | Milestone | Work | Exit condition | Est. | State |
| ----- | --------- | ---- | -------------- | ---- | ----- |
| PA-01 | Data + baseline | Dataset provenance/hash, stratified split, sklearn pipeline vs. dummy baseline, versioned artifact + manifest | Report with baseline and untouched-test evaluation; test reproduces stored metrics | done | validated (local) |
| PA-02 | Minimal API + CI | FastAPI `POST /predict`, `GET /health`, `GET /ready`, `GET /models`; Pydantic validation from manifest schema; hash-checked artifact load; GitHub Actions running pytest on every push/PR | Prediction equals offline run; invalid inputs rejected with 422; tampered artifact refused; CI green on GitHub | 8–12 h | validated |
| PA-03 | Model v2 + explainability | Train v2 (tree-based) selected by CV on train; decision threshold for the dataset's 5:1 cost matrix; `modelVersion` selects v1/v2; `POST /explain` (SHAP top factors) for both; model card (EN) comparing versions | v2 vs v1 vs baseline on untouched test; SHAP values + base value equal model output; model card lists data, metrics, limits, risks | 10–15 h | in progress |
| PA-04 | Persistence + monitoring | `docker compose` (API + PostgreSQL); versioned migrations; PredictionLog (requestId, version, latency, result); DB-outage policy; rate limiting; Evidently drift report from logged inputs | Every inference linked to an artifact; DB down follows documented policy; 429 over limit; drift report generated from real logs | 12–18 h | pending |
| PA-05 | Delivery | Multi-stage production Dockerfile; CI extended (build → push → deploy); AWS deploy; p50/p95 latency under a defined load; README EN/ES with architecture diagram, technical decisions, AI-usage note; short demo video | Fresh clone runs with `docker compose up`; CI green end to end; public demo URL; every README number traced to `docs/validation.md` | 12–20 h | pending |

Estimates are effort for one person; revisit after PA-02.

Out of scope until asked: PyTorch, LIME, own frontend.
