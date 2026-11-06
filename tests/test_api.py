import json

import joblib
import pytest
from fastapi.testclient import TestClient

import train
from app.main import ROOT, app


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


def test_predict_matches_offline_model(client, rows):
    entry = json.loads((ROOT / "models/manifest.json").read_text())["models"][-1]
    model = joblib.load(ROOT / entry["artifact"])
    for i in range(len(rows)):
        res = client.post("/predict", json=as_payload(rows, i))
        assert res.status_code == 200
        body = res.json()
        assert body["model_version"] == entry["version"]
        assert body["probability_bad"] == pytest.approx(model.predict_proba(rows.iloc[[i]])[0, 1])
        assert body["prediction"] == ("bad" if model.predict(rows.iloc[[i]])[0] == 1 else "good")


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


def test_health_ready_models(client):
    assert client.get("/health").json() == {"status": "ok"}
    assert client.get("/ready").status_code == 200
    body = client.get("/models").json()
    assert [m["version"] for m in body["loaded"]] == [body["latest"]]
    assert body["unavailable"] == {}


def test_tampered_artifact_is_refused(tmp_path, monkeypatch, rows):
    manifest = json.loads((ROOT / "models/manifest.json").read_text())
    manifest["models"][-1]["artifact_sha256"] = "0" * 64
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps(manifest))
    monkeypatch.setenv("PREDICTAPI_MANIFEST", str(path))

    with TestClient(app) as c:
        assert c.get("/health").status_code == 200
        assert c.get("/ready").status_code == 503
        assert c.post("/predict", json=as_payload(rows, 0)).status_code == 503
        assert c.get("/models").json()["unavailable"] == {"v1": "artifact hash mismatch"}
