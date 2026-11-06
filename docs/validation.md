# Validation evidence

## PA-01 — Data + baseline (2026-10-09, local)

Environment: Windows 11, Python 3.12.15 (uv), scikit-learn/pandas versions in `models/manifest.json`.

```
uv run python training/train.py
uv run pytest -q   # 1 passed
```

Dataset: OpenML 31 (UCI Statlog German Credit, CC BY 4.0), 1000 rows, positive class `bad` (30%). Stratified 80/20 split, seed 42.

| Model | CV5 train ROC AUC | Test ROC AUC | Test accuracy | Test F1 (bad) | Test Brier |
| --- | --- | --- | --- | --- | --- |
| Dummy (prior) | — | 0.500 | 0.700 | 0.000 | 0.210 |
| LogisticRegression v1 | 0.784 ± 0.017 | 0.804 | 0.780 | 0.593 | 0.155 |

`tests/test_training.py` checks: artifact SHA-256 matches manifest, dataset hash matches, reloaded artifact reproduces stored test metrics, model beats baseline.

Open items: threshold fixed at 0.5 (German Credit's 5:1 cost matrix not applied yet; handled in PA-03). CI not set up yet (PA-02).

## PA-02 — Minimal API + CI (2026-11-05, local)

```
uv run pytest -q   # 9 passed
uv run uvicorn app.main:app --port 8765
curl localhost:8765/ready      # {"status":"ready","model_version":"v1"}
curl -X POST localhost:8765/predict -d '<row: checking_status "<0", duration 48, credit_amount 5951, age 22, ...>'
# {"prediction":"bad","probability_bad":0.6501,"model_version":"v1","request_id":"..."}
```

`tests/test_api.py` checks: API probability and label equal the offline model on 5 dataset rows; missing field, unknown category, negative amount, wrong type and extra field each return 422; with a tampered manifest hash `/health` stays 200 while `/ready` and `/predict` return 503 and `/models` reports `artifact hash mismatch`.

CI on GitHub: PR #2, runs 42134373517 and 42134421566, both `success` (`uv sync --locked` + `pytest`, ubuntu-latest).

## PA-03 — Model v2 + explainability (2026-11-05, local)

```
uv run python training/train.py v1   # retrained: models/v1/model.joblib byte-identical to PA-01 (cmp), same SHA-256
uv run python training/train.py v2
uv run pytest -q                     # 15 passed
```

Thresholds chosen on out-of-fold train predictions under the 5:1 cost matrix: v1 0.13, v2 0.14, baseline 0.01.
v2 grid (5-fold CV on train, ROC AUC): n_estimators {100, 300} × learning_rate {0.03, 0.1} × max_depth {2, 3} → 100 / 0.1 / 2.

| Model | Threshold | CV5 train ROC AUC | Test ROC AUC | Test accuracy | Test F1 (bad) | Test Brier | Test avg. cost |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Baseline | 0.01 | — | 0.500 | 0.300 | 0.462 | 0.210 | 0.70 |
| v1 | 0.50 | 0.784 ± 0.017 | 0.804 | 0.780 | 0.593 | 0.155 | 0.78 |
| v1 | 0.13 | 0.784 ± 0.017 | 0.804 | 0.570 | 0.552 | 0.155 | 0.57 |
| v2 | 0.50 | 0.774 ± 0.011 | 0.792 | 0.770 | 0.566 | 0.163 | 0.83 |
| v2 | 0.14 | 0.774 ± 0.011 | 0.792 | 0.540 | 0.545 | 0.163 | 0.56 |

Rows at 0.50 computed ad hoc with `train.metrics(model, X_test, y_test, 0.5)` for comparison; they are not served.
Default stays v1 (higher CV AUC on train). Manifest `default: "v1"`.

`tests/test_api.py` adds: both versions match the offline model at their threshold; `/explain` returns 20 contributions sorted by |SHAP| whose sum plus base equals the log-odds of the returned probability (abs 1e-6), for v1 (LinearExplainer) and v2 (TreeExplainer); unknown version → 404; tampered default → 503 while the other version keeps serving.

Sample `/explain` (dataset row 1, duration 48, credit_amount 5951, age 22): v1 P(bad)=0.559 → bad; top factors duration +0.755, checking_status +0.375, credit_amount +0.336, savings_status +0.328, installment_commitment −0.320. v2 agrees on the top three.
