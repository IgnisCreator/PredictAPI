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

Open items: threshold fixed at 0.5 (German Credit's 5:1 cost matrix not applied yet; revisit in model card, PA-03). CI not run yet (PA-05).
