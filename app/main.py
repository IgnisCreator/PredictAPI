"""PredictAPI: credit-risk predictions served from versioned, hash-checked artifacts.

Run: uv run fastapi dev app/main.py  (Swagger UI at /docs)
"""

import hashlib
import json
import os
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Literal

import joblib
import pandas as pd
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, ConfigDict, Field, create_model

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_MANIFEST = ROOT / "models" / "manifest.json"


def load_models(manifest_path):
    """Return ({version: (entry, model)}, {version: error}) for every manifest entry."""
    models, errors = {}, {}
    for entry in json.loads(Path(manifest_path).read_text())["models"]:
        artifact = ROOT / entry["artifact"]
        if not artifact.is_file():
            errors[entry["version"]] = "artifact missing"
        elif hashlib.sha256(artifact.read_bytes()).hexdigest() != entry["artifact_sha256"]:
            errors[entry["version"]] = "artifact hash mismatch"
        else:
            # joblib usa pickle (puede ejecutar código): solo se carga tras verificar el hash
            models[entry["version"]] = (entry, joblib.load(artifact))
    return models, errors


def request_model(entry):
    """Build the input schema from the manifest so API and model can never drift apart."""
    fields = {}
    for name, dtype in entry["features"].items():
        if name in entry["categories"]:
            fields[name] = (Literal[tuple(entry["categories"][name])], ...)
        else:
            fields[name] = (int if dtype.startswith("int") else float, Field(ge=0))
    return create_model("CreditApplication", __config__=ConfigDict(extra="forbid"), **fields)


CreditApplication = request_model(json.loads(DEFAULT_MANIFEST.read_text())["models"][-1])


class Prediction(BaseModel):
    prediction: Literal["bad", "good"]
    probability_bad: float
    model_version: str
    request_id: str


@asynccontextmanager
async def lifespan(app):
    manifest_path = os.environ.get("PREDICTAPI_MANIFEST", DEFAULT_MANIFEST)
    app.state.models, app.state.errors = load_models(manifest_path)
    app.state.latest = json.loads(Path(manifest_path).read_text())["models"][-1]["version"]
    yield


app = FastAPI(title="PredictAPI", version="0.2.0", lifespan=lifespan)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/ready")
def ready():
    if app.state.latest not in app.state.models:
        raise HTTPException(503, detail={"status": "not ready", "errors": app.state.errors})
    return {"status": "ready", "model_version": app.state.latest}


@app.get("/models")
def list_models():
    public = ("version", "created_at", "estimator", "artifact_sha256", "metrics")
    return {
        "latest": app.state.latest,
        "loaded": [{k: entry[k] for k in public} for entry, _ in app.state.models.values()],
        "unavailable": app.state.errors,
    }


@app.post("/predict", response_model=Prediction)
def predict(application: CreditApplication):
    if app.state.latest not in app.state.models:
        raise HTTPException(503, detail="model not loaded")
    _, model = app.state.models[app.state.latest]
    X = pd.DataFrame([application.model_dump()])
    return Prediction(
        prediction="bad" if model.predict(X)[0] == 1 else "good",
        probability_bad=float(model.predict_proba(X)[0, 1]),
        model_version=app.state.latest,
        request_id=str(uuid.uuid4()),
    )
