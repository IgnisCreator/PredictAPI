"""Train a PredictAPI model version on German Credit and register it in models/manifest.json.

Run: uv run python training/train.py v1   (logistic regression)
     uv run python training/train.py v2   (gradient boosting, tuned by CV)
"""

import hashlib
import json
import sys
from datetime import datetime, timezone
from importlib.metadata import version
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.datasets import fetch_openml
from sklearn.dummy import DummyClassifier
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, brier_score_loss, f1_score, roc_auc_score
from sklearn.model_selection import GridSearchCV, cross_val_predict, cross_val_score, train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

ROOT = Path(__file__).resolve().parent.parent
SEED = 42
OPENML_ID = 31  # credit-g v1 = UCI Statlog German Credit (CC BY 4.0)
# Matriz de costo publicada con el dataset: aprobar a un mal pagador cuesta 5, rechazar a uno bueno cuesta 1
COST_FN, COST_FP = 5, 1


def load_data():
    X, y = fetch_openml(data_id=OPENML_ID, as_frame=True, return_X_y=True, data_home=ROOT / "data")
    # Clase positiva = "bad" (incumplimiento), que es lo que el banco quiere detectar
    return X, (y == "bad").astype(int)


def split(X, y):
    return train_test_split(X, y, test_size=0.2, stratify=y, random_state=SEED)


def frame_sha256(X, y):
    csv = pd.concat([X, y.rename("bad")], axis=1).to_csv(index=False, lineterminator="\n")
    return hashlib.sha256(csv.encode()).hexdigest()


def build_pipeline(X, clf):
    cat = X.select_dtypes("category").columns.tolist()
    num = X.select_dtypes("number").columns.tolist()
    prep = ColumnTransformer([
        ("num", StandardScaler(), num),
        ("cat", OneHotEncoder(handle_unknown="ignore"), cat),
    ])
    return Pipeline([("prep", prep), ("clf", clf)])


def build_model(model_version, X, X_train, y_train):
    """Return (fitted pipeline, unfitted pipeline with the chosen params, explainer kind, params)."""
    if model_version == "v1":
        model = build_pipeline(X, LogisticRegression(max_iter=1000))
        return model.fit(X_train, y_train), build_pipeline(X, LogisticRegression(max_iter=1000)), "linear", {}
    if model_version == "v2":
        search = GridSearchCV(
            build_pipeline(X, GradientBoostingClassifier(random_state=SEED)),
            {"clf__n_estimators": [100, 300], "clf__learning_rate": [0.03, 0.1], "clf__max_depth": [2, 3]},
            cv=5, scoring="roc_auc",
        ).fit(X_train, y_train)
        unfitted = build_pipeline(X, GradientBoostingClassifier(random_state=SEED))
        return search.best_estimator_, unfitted.set_params(**search.best_params_), "tree", search.best_params_
    raise SystemExit(f"unknown version {model_version!r}; expected v1 or v2")


def cost(y, pred):
    """Average cost per applicant under the dataset's cost matrix."""
    fn = int(((pred == 0) & (y == 1)).sum())
    fp = int(((pred == 1) & (y == 0)).sum())
    return (COST_FN * fn + COST_FP * fp) / len(y)


def choose_threshold(model, X_train, y_train):
    # Probabilidades fuera de fold: el umbral se elige sin mirar el test
    proba = cross_val_predict(model, X_train, y_train, cv=5, method="predict_proba")[:, 1]
    grid = np.round(np.linspace(0.01, 0.99, 99), 2)
    return float(grid[np.argmin([cost(y_train.to_numpy(), (proba >= t).astype(int)) for t in grid])])


def metrics(model, X, y, threshold):
    proba = model.predict_proba(X)[:, 1]
    pred = (proba >= threshold).astype(int)
    return {
        "roc_auc": round(roc_auc_score(y, proba), 4),
        "accuracy": round(accuracy_score(y, pred), 4),
        "f1_bad": round(f1_score(y, pred, zero_division=0), 4),
        "brier": round(brier_score_loss(y, proba), 4),
        "avg_cost": round(cost(y.to_numpy(), pred), 4),
    }


def main(model_version):
    X, y = load_data()
    X_train, X_test, y_train, y_test = split(X, y)

    model, unfitted, explainer, params = build_model(model_version, X, X_train, y_train)
    cv_auc = cross_val_score(unfitted, X_train, y_train, cv=5, scoring="roc_auc")
    threshold = choose_threshold(unfitted, X_train, y_train)
    baseline = DummyClassifier(strategy="prior")
    baseline_threshold = choose_threshold(baseline, X_train, y_train)
    baseline.fit(X_train, y_train)

    out_dir = ROOT / "models" / model_version
    out_dir.mkdir(parents=True, exist_ok=True)
    artifact = out_dir / "model.joblib"
    joblib.dump(model, artifact)

    entry = {
        "version": model_version,
        "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "artifact": artifact.relative_to(ROOT).as_posix(),
        "artifact_sha256": hashlib.sha256(artifact.read_bytes()).hexdigest(),
        "estimator": f"{type(model[-1]).__name__} + StandardScaler/OneHotEncoder",
        "params": params,
        "positive_class": "bad",
        "threshold": threshold,
        "cost_matrix": {"false_negative": COST_FN, "false_positive": COST_FP},
        "explainer": explainer,
        "features": {c: str(X[c].dtype) for c in X.columns},
        "categories": {c: X[c].cat.categories.tolist() for c in X.select_dtypes("category")},
        "dataset": {
            "source": f"OpenML data_id={OPENML_ID} (UCI Statlog German Credit)",
            "license": "CC BY 4.0",
            "rows": len(X),
            "sha256": frame_sha256(X, y),
            "split": {"test_size": 0.2, "stratified": True, "seed": SEED,
                      "train_rows": len(X_train), "test_rows": len(X_test)},
        },
        "metrics": {
            "cv5_train_roc_auc_mean": round(cv_auc.mean(), 4),
            "cv5_train_roc_auc_std": round(cv_auc.std(), 4),
            "test": metrics(model, X_test, y_test, threshold),
            "baseline_threshold": baseline_threshold,
            "baseline_test": metrics(baseline, X_test, y_test, baseline_threshold),
        },
        "libraries": {lib: version(lib) for lib in ("scikit-learn", "pandas", "numpy", "joblib")},
        "python": sys.version.split()[0],
    }
    if explainer == "linear":
        # SHAP lineal con features independientes solo necesita la media de train transformado
        entry["shap_background"] = np.asarray(model[0].transform(X_train).mean(axis=0)).ravel().round(6).tolist()

    manifest_path = ROOT / "models" / "manifest.json"
    manifest = json.loads(manifest_path.read_text()) if manifest_path.exists() else {"models": []}
    manifest["models"] = sorted(
        [m for m in manifest["models"] if m["version"] != model_version] + [entry], key=lambda m: m["version"]
    )
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")

    print(json.dumps({"threshold": threshold, "params": entry["params"], **entry["metrics"]}, indent=2))


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "v1")
