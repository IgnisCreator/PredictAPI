"""Train PredictAPI v1 on German Credit and write models/v1 + models/manifest.json.

Run: uv run python training/train.py
"""

import hashlib
import json
import sys
from datetime import datetime, timezone
from importlib.metadata import version
from pathlib import Path

import joblib
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.datasets import fetch_openml
from sklearn.dummy import DummyClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, brier_score_loss, f1_score, roc_auc_score
from sklearn.model_selection import cross_val_score, train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

ROOT = Path(__file__).resolve().parent.parent
SEED = 42
VERSION = "v1"
OPENML_ID = 31  # credit-g v1 = UCI Statlog German Credit (CC BY 4.0)


def load_data():
    X, y = fetch_openml(data_id=OPENML_ID, as_frame=True, return_X_y=True, data_home=ROOT / "data")
    # Clase positiva = "bad" (incumplimiento), que es lo que el banco quiere detectar
    return X, (y == "bad").astype(int)


def frame_sha256(X, y):
    csv = pd.concat([X, y.rename("bad")], axis=1).to_csv(index=False, lineterminator="\n")
    return hashlib.sha256(csv.encode()).hexdigest()


def build_pipeline(X):
    cat = X.select_dtypes("category").columns.tolist()
    num = X.select_dtypes("number").columns.tolist()
    prep = ColumnTransformer([
        ("num", StandardScaler(), num),
        ("cat", OneHotEncoder(handle_unknown="ignore"), cat),
    ])
    return Pipeline([("prep", prep), ("clf", LogisticRegression(max_iter=1000))])


def metrics(model, X, y):
    proba = model.predict_proba(X)[:, 1]
    pred = model.predict(X)
    return {
        "roc_auc": round(roc_auc_score(y, proba), 4),
        "accuracy": round(accuracy_score(y, pred), 4),
        "f1_bad": round(f1_score(y, pred, zero_division=0), 4),
        "brier": round(brier_score_loss(y, proba), 4),
    }


def main():
    X, y = load_data()
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, stratify=y, random_state=SEED
    )

    model = build_pipeline(X)
    cv_auc = cross_val_score(model, X_train, y_train, cv=5, scoring="roc_auc")
    model.fit(X_train, y_train)
    baseline = DummyClassifier(strategy="prior").fit(X_train, y_train)

    out_dir = ROOT / "models" / VERSION
    out_dir.mkdir(parents=True, exist_ok=True)
    artifact = out_dir / "model.joblib"
    joblib.dump(model, artifact)

    entry = {
        "version": VERSION,
        "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "artifact": artifact.relative_to(ROOT).as_posix(),
        "artifact_sha256": hashlib.sha256(artifact.read_bytes()).hexdigest(),
        "estimator": "LogisticRegression + StandardScaler/OneHotEncoder",
        "positive_class": "bad",
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
            "test": metrics(model, X_test, y_test),
            "baseline_test": metrics(baseline, X_test, y_test),
        },
        "libraries": {lib: version(lib) for lib in ("scikit-learn", "pandas", "numpy", "joblib")},
        "python": sys.version.split()[0],
    }

    manifest_path = ROOT / "models" / "manifest.json"
    manifest = json.loads(manifest_path.read_text()) if manifest_path.exists() else {"models": []}
    manifest["models"] = [m for m in manifest["models"] if m["version"] != VERSION] + [entry]
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")

    print(json.dumps(entry["metrics"], indent=2))


if __name__ == "__main__":
    main()
