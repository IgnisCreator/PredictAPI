"""Run against a real PostgreSQL: set DATABASE_URL (CI service, or `docker compose up db`)."""

import json
import os

import pytest
from fastapi.testclient import TestClient

import train
from app import db
from app.main import ROOT, app

pytestmark = pytest.mark.skipif(not os.environ.get("DATABASE_URL"), reason="DATABASE_URL not set")
MANIFEST = json.loads((ROOT / "models/manifest.json").read_text())


@pytest.fixture(scope="module")
def payload():
    X, _ = train.load_data()
    return json.loads(X.head(1).to_json(orient="records"))[0]


def logged_row(request_id):
    with db.connect() as conn:
        return conn.execute(
            "select endpoint, model_version, model_sha256, features, prediction, probability_bad"
            " from prediction_log where request_id = %s", (request_id,)
        ).fetchone()


@pytest.mark.parametrize("endpoint,version", [("predict", "v1"), ("explain", "v2")])
def test_inference_is_logged_and_linked_to_artifact(payload, endpoint, version):
    with TestClient(app) as c:
        body = c.post(f"/{endpoint}", params={"model_version": version}, json=payload).json()
    assert body["logged"] is True
    entry = next(e for e in MANIFEST["models"] if e["version"] == version)
    assert logged_row(body["request_id"]) == (
        endpoint, version, entry["artifact_sha256"], payload, body["prediction"], body["probability_bad"]
    )


def test_migrations_are_idempotent():
    db.migrate()
    db.migrate()
    with db.connect() as conn:
        versions = [r[0] for r in conn.execute("select version from schema_migrations order by version")]
    assert versions == sorted(p.name for p in db.MIGRATIONS.glob("*.sql"))
