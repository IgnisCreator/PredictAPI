import hashlib
import json
import sys
from pathlib import Path

import joblib
from sklearn.model_selection import train_test_split

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "training"))
import train  # noqa: E402


def test_artifact_matches_manifest_and_reproduces_metrics():
    entry = json.loads((ROOT / "models/manifest.json").read_text())["models"][-1]
    artifact = ROOT / entry["artifact"]
    assert hashlib.sha256(artifact.read_bytes()).hexdigest() == entry["artifact_sha256"]

    X, y = train.load_data()
    assert train.frame_sha256(X, y) == entry["dataset"]["sha256"]
    split = entry["dataset"]["split"]
    _, X_test, _, y_test = train_test_split(
        X, y, test_size=split["test_size"], stratify=y, random_state=split["seed"]
    )

    test_metrics = train.metrics(joblib.load(artifact), X_test, y_test)
    assert test_metrics == entry["metrics"]["test"]
    assert test_metrics["roc_auc"] > entry["metrics"]["baseline_test"]["roc_auc"]
