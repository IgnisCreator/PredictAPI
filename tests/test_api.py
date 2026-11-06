import json
import math

import joblib
import pytest
from fastapi.testclient import TestClient

import train
from app.main import ROOT, app

MANIFEST = json.loads((ROOT / "models/manifest.json").read_text())
VERSIONS = [e["version"] for e in MANIFEST["models"]]


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="module")
def rows():
    X, _ = train.load_data()
    return X.head(5)


def as_payload(X, i):
    return json.loads(X.iloc[[i]].to_json(orient="records"))[0]


@pytest.mark.parametrize("version", VERSIONS)
def test_predict_matches_offline_model(client, rows, version):
    entry = next(e for e in MANIFEST["models"] if e["version"] == version)
    model = joblib.load(ROOT / entry["artifact"])
    for i in range(len(rows)):
        res = client.post("/predict", params={"model_version": version}, json=as_payload(rows, i))
        assert res.status_code == 200
        body = res.json()
        proba = model.predict_proba(rows.iloc[[i]])[0, 1]
        assert body["model_version"] == version
        assert body["probability_bad"] == pytest.approx(proba)
        assert body["prediction"] == ("bad" if proba >= entry["threshold"] else "good")


def test_default_version_used_without_param(client, rows):
    assert client.post("/predict", json=as_payload(rows, 0)).json()["model_version"] == MANIFEST["default"]


@pytest.mark.parametrize("version", VERSIONS)
def test_explanation_adds_up_to_model_output(client, rows, version):
    for i in range(len(rows)):
        body = client.post("/explain", params={"model_version": version}, json=as_payload(rows, i)).json()
        shap_values = [c["shap"] for c in body["contributions"]]
        assert len(shap_values) == len(rows.columns)
        assert shap_values == sorted(shap_values, key=abs, reverse=True)
        assert body["base_log_odds"] + sum(shap_values) == pytest.approx(body["log_odds"])
        # La suma de SHAP (en log-odds) debe reproducir la probabilidad que da el modelo
        assert 1 / (1 + math.exp(-body["log_odds"])) == pytest.approx(body["probability_bad"], abs=1e-6)


@pytest.mark.parametrize("change", [
    lambda p: p.pop("age"),                            # campo faltante
    lambda p: p.update(purpose="crypto"),              # categoría desconocida
    lambda p: p.update(credit_amount=-100),            # monto negativo
    lambda p: p.update(credit_amount="mucho"),         # tipo incorrecto
    lambda p: p.update(salary=1000),                   # campo no esperado
])
def test_invalid_input_rejected(client, rows, change):
    payload = as_payload(rows, 0)
    change(payload)
    assert client.post("/predict", json=payload).status_code == 422


def test_unknown_version_is_404(client, rows):
    assert client.post("/predict", params={"model_version": "v9"}, json=as_payload(rows, 0)).status_code == 404


def test_health_ready_models(client):
    assert client.get("/health").json() == {"status": "ok"}
    assert client.get("/ready").status_code == 200
    body = client.get("/models").json()
    assert sorted(m["version"] for m in body["loaded"]) == VERSIONS
    assert body["unavailable"] == {}


def test_tampered_artifact_is_refused(tmp_path, monkeypatch, rows):
    manifest = json.loads((ROOT / "models/manifest.json").read_text())
    tampered = manifest["default"]
    next(e for e in manifest["models"] if e["version"] == tampered)["artifact_sha256"] = "0" * 64
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps(manifest))
    monkeypatch.setenv("PREDICTAPI_MANIFEST", str(path))

    with TestClient(app) as c:
        assert c.get("/health").status_code == 200
        assert c.get("/ready").status_code == 503
        assert c.post("/predict", json=as_payload(rows, 0)).status_code == 503
        assert c.get("/models").json()["unavailable"] == {tampered: "artifact hash mismatch"}
        other = next(v for v in VERSIONS if v != tampered)
        assert c.post("/predict", params={"model_version": other}, json=as_payload(rows, 0)).status_code == 200
