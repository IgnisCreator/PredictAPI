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

Open item: CI run on GitHub (PR #2) pending at time of writing.
