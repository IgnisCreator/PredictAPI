import hashlib
import json
from pathlib import Path

import joblib
import pytest

import train

ROOT = Path(__file__).resolve().parent.parent
ENTRIES = json.loads((ROOT / "models/manifest.json").read_text())["models"]


@pytest.mark.parametrize("entry", ENTRIES, ids=[e["version"] for e in ENTRIES])
def test_artifact_matches_manifest_and_reproduces_metrics(entry):
    artifact = ROOT / entry["artifact"]
    assert hashlib.sha256(artifact.read_bytes()).hexdigest() == entry["artifact_sha256"]

    X, y = train.load_data()
    assert train.frame_sha256(X, y) == entry["dataset"]["sha256"]
    _, X_test, _, y_test = train.split(X, y)

    test_metrics = train.metrics(joblib.load(artifact), X_test, y_test, entry["threshold"])
    assert test_metrics == entry["metrics"]["test"]
    baseline = entry["metrics"]["baseline_test"]
    assert test_metrics["roc_auc"] > baseline["roc_auc"]
    assert test_metrics["avg_cost"] < baseline["avg_cost"]
