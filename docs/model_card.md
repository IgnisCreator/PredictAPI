# Model card — PredictAPI credit-risk models

Every number below comes from `models/manifest.json` and the runs recorded in `docs/validation.md`.

## Intended use

Portfolio demonstration of a traceable, explainable ML service. It estimates the probability that a loan applicant from the German Credit dataset is a **bad** credit risk and explains which inputs drove that estimate.

**Not for real lending decisions.** The data is small, old and from another country (see Limitations), and the models have not been validated for fairness.

## Data

| | |
|---|---|
| Source | UCI Statlog German Credit, via OpenML `data_id=31` |
| License | CC BY 4.0 |
| Rows | 1,000 applicants (700 good, 300 bad); 20 features: 13 categorical, 7 numeric |
| Split | Stratified 80/20, seed 42 → 800 train, 200 test. The test set is used only for the final report. |
| Integrity | SHA-256 of the dataset recorded in the manifest and checked in tests |

## Models

| Version | Estimator | Selection | Decision threshold on P(bad) |
|---|---|---|---|
| **v1 (default)** | Logistic regression, StandardScaler + OneHotEncoder | Fixed configuration | 0.13 |
| v2 | Gradient boosting (100 trees, depth 2, learning rate 0.1) | 5-fold CV grid search on train, ROC AUC | 0.14 |
| Baseline | `DummyClassifier(strategy="prior")` | — | 0.01 (always predicts bad) |

**Why the threshold is not 0.5.** The dataset ships with a cost matrix: approving a bad applicant costs 5, rejecting a good one costs 1. Each model's threshold is chosen by minimising that cost on out-of-fold predictions **on the training set only**.

**Why v1 stays the default.** v2's CV ROC AUC on train (0.774 ± 0.011) is lower than v1's (0.784 ± 0.017). CV on train is the selection criterion, so v1 stays the default. v2 is served for comparison with `?model_version=v2`.

## Results (untouched test set, 200 applicants)

| Model | Threshold | ROC AUC | Accuracy | F1 (bad) | Brier | Avg. cost per applicant |
|---|---|---|---|---|---|---|
| Baseline | 0.01 | 0.500 | 0.300 | 0.462 | 0.210 | 0.70 |
| v1 | 0.50 | 0.804 | 0.780 | 0.593 | 0.155 | 0.78 |
| **v1** | **0.13** | **0.804** | 0.570 | 0.552 | **0.155** | **0.57** |
| v2 | 0.50 | 0.792 | 0.770 | 0.566 | 0.163 | 0.83 |
| v2 | 0.14 | 0.792 | 0.540 | 0.545 | 0.163 | 0.56 |

Key reading: at the default 0.5 threshold both models cost **more** than rejecting everyone (0.78 and 0.83 vs. 0.70). The cost-based threshold brings them below the baseline. Accuracy drops because the models now reject more applicants on purpose. On 200 test rows, the 0.01 cost gap between v1 and v2 is within noise.

## Explanations

`POST /explain` returns SHAP values in log-odds space, with one-hot columns summed back to their original feature:

- v1: `LinearExplainer` with an independent masker, using the training-set mean as background.
- v2: `TreeExplainer` (tree-path-dependent).

Tests check that base value + sum of contributions reproduces the model's probability for every explained row.

Explanations describe the **model**, not causes in the real world.

## Limitations and risks

- **Small and dated data.** 1,000 rows collected in 1970s Germany; currency (Deutsche Mark), products and lending norms do not transfer to today or to Chile.
- **Sensitive attributes.** `personal_status` mixes sex and marital status, and `foreign_worker` and `age` are inputs. A model using them can discriminate; no fairness audit has been done. A production model would need to remove or audit them and measure disparate impact.
- **Uncertainty.** With 200 test rows, metric differences of a few hundredths are not significant.
- **Calibration.** The threshold assumes reasonably calibrated probabilities (Brier 0.155–0.163); it was not recalibrated.
- **Drift.** Live inputs are not monitored yet; drift reporting arrives in PA-04.

## Reproduce

```
uv run python training/train.py v1
uv run python training/train.py v2
uv run pytest -q
```
