"""PredictAPI: credit-risk predictions served from versioned, hash-checked artifacts.

Run: uv run fastapi dev app/main.py  (Swagger UI at /docs)
"""

import hashlib
import json
import logging
import os
import time
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Literal

import joblib
import numpy as np
import pandas as pd
import psycopg
import shap
from fastapi import Depends, FastAPI, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field, create_model

from app import db

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_MANIFEST = ROOT / "models" / "manifest.json"


def request_model(entry):
    """Build the input schema from the manifest so API and model can never drift apart."""
    fields = {}
    for name, dtype in entry["features"].items():
        if name in entry["categories"]:
            fields[name] = (Literal[tuple(entry["categories"][name])], ...)
        else:
            fields[name] = (int if dtype.startswith("int") else float, Field(ge=0))
    return create_model("CreditApplication", __config__=ConfigDict(extra="forbid"), **fields)


_manifest = json.loads(DEFAULT_MANIFEST.read_text())
CreditApplication = request_model(_manifest["models"][-1])


def make_explainer(entry, model):
    if entry["explainer"] == "linear":
        background = shap.maskers.Independent(np.array([entry["shap_background"]]))
        return shap.LinearExplainer(model[-1], background)
    return shap.TreeExplainer(model[-1])


def load_models(manifest_path):
    """Return ({version: (entry, model, explainer)}, {version: error}) for every manifest entry."""
    models, errors = {}, {}
    for entry in json.loads(Path(manifest_path).read_text())["models"]:
        artifact = ROOT / entry["artifact"]
        if list(entry["features"]) != list(CreditApplication.model_fields):
            errors[entry["version"]] = "feature schema differs from the API schema"
        elif not artifact.is_file():
            errors[entry["version"]] = "artifact missing"
        elif hashlib.sha256(artifact.read_bytes()).hexdigest() != entry["artifact_sha256"]:
            errors[entry["version"]] = "artifact hash mismatch"
        else:
            # joblib usa pickle (puede ejecutar código): solo se carga tras verificar el hash
            model = joblib.load(artifact)
            models[entry["version"]] = (entry, model, make_explainer(entry, model))
    return models, errors


class Prediction(BaseModel):
    prediction: Literal["bad", "good"]
    probability_bad: float
    threshold: float
    model_version: str
    request_id: str
    logged: bool = False


class Contribution(BaseModel):
    feature: str
    value: str | int | float
    shap: float


class Explanation(Prediction):
    base_log_odds: float
    log_odds: float
    contributions: list[Contribution]


@asynccontextmanager
async def lifespan(app):
    manifest_path = os.environ.get("PREDICTAPI_MANIFEST", DEFAULT_MANIFEST)
    manifest = json.loads(Path(manifest_path).read_text())
    app.state.models, app.state.errors = load_models(manifest_path)
    app.state.default = manifest.get("default", manifest["models"][-1]["version"])
    app.state.rate_limit = int(os.environ.get("RATE_LIMIT_PER_MINUTE", 60))
    app.state.window, app.state.hits = None, {}
    db.down_until = 0.0
    if os.environ.get("DATABASE_URL"):
        try:
            db.migrate()
        except psycopg.Error as exc:
            logging.getLogger("predictapi").warning("migrations not applied, predictions will not be logged: %s", exc)
    yield


app = FastAPI(title="PredictAPI", version="0.4.0", lifespan=lifespan)


def rate_limit(request: Request):
    # ponytail: ventana fija de 1 minuto en memoria por proceso; con varias réplicas, límite en Redis o el gateway
    window = int(time.time() // 60)
    if window != app.state.window:
        app.state.window, app.state.hits = window, {}
    client = request.client.host if request.client else "unknown"
    app.state.hits[client] = app.state.hits.get(client, 0) + 1
    if app.state.hits[client] > app.state.rate_limit:
        retry_after = str(60 - int(time.time()) % 60)
        raise HTTPException(429, detail="rate limit exceeded", headers={"Retry-After": retry_after})


def resolve(model_version):
    model_version = model_version or app.state.default
    if model_version in app.state.errors:
        raise HTTPException(503, detail=f"model {model_version} not loaded: {app.state.errors[model_version]}")
    if model_version not in app.state.models:
        raise HTTPException(404, detail=f"unknown model version {model_version!r}")
    return model_version, *app.state.models[model_version]


def score(application, model_version):
    model_version, entry, model, explainer = resolve(model_version)
    X = pd.DataFrame([application.model_dump()])
    proba = float(model.predict_proba(X)[0, 1])
    prediction = Prediction(
        prediction="bad" if proba >= entry["threshold"] else "good",
        probability_bad=proba,
        threshold=entry["threshold"],
        model_version=model_version,
        request_id=str(uuid.uuid4()),
    )
    return prediction, X, entry, model, explainer


def record(prediction, endpoint, entry, X, started):
    prediction.logged = db.log_prediction({
        "request_id": prediction.request_id,
        "endpoint": endpoint,
        "model_version": prediction.model_version,
        "model_sha256": entry["artifact_sha256"],
        "features": X.to_dict("records")[0],  # tipos nativos de Python, serializables a JSON
        "probability_bad": prediction.probability_bad,
        "threshold": prediction.threshold,
        "prediction": prediction.prediction,
        "latency_ms": (time.perf_counter() - started) * 1000,
    })
    return prediction


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/ready")
def ready():
    if app.state.default not in app.state.models:
        raise HTTPException(503, detail={"status": "not ready", "errors": app.state.errors})
    return {"status": "ready", "default_model": app.state.default, "database": db.status()}


@app.get("/models")
def list_models():
    public = ("version", "created_at", "estimator", "params", "threshold", "artifact_sha256", "metrics")
    return {
        "default": app.state.default,
        "loaded": [{k: entry.get(k) for k in public} for entry, _, _ in app.state.models.values()],
        "unavailable": app.state.errors,
    }


@app.post("/predict", response_model=Prediction, dependencies=[Depends(rate_limit)])
def predict(application: CreditApplication, model_version: str | None = None):
    started = time.perf_counter()
    prediction, X, entry, _, _ = score(application, model_version)
    return record(prediction, "predict", entry, X, started)


@app.post("/explain", response_model=Explanation, dependencies=[Depends(rate_limit)])
def explain(application: CreditApplication, model_version: str | None = None):
    """SHAP contribution of each input to the log-odds of `bad`, largest first."""
    started = time.perf_counter()
    prediction, X, entry, model, explainer = score(application, model_version)
    prep = model[0]
    Xt = prep.transform(X)
    result = explainer(Xt.toarray() if hasattr(Xt, "toarray") else Xt)
    # Las columnas one-hot se suman de vuelta a su feature original (SHAP es aditivo)
    owners = []
    for name, transformer, cols in prep.transformers_:
        if name == "num":
            owners += cols
        elif name == "cat":
            owners += [c for c, cats in zip(cols, transformer.categories_) for _ in cats]
    per_feature = pd.Series(result.values[0], index=owners).groupby(level=0, sort=False).sum()
    base = float(np.ravel(result.base_values)[0])
    row = X.iloc[0]
    contributions = [
        Contribution(feature=f, value=row[f].item() if hasattr(row[f], "item") else row[f], shap=float(v))
        for f, v in per_feature.sort_values(key=abs, ascending=False).items()
    ]
    record(prediction, "explain", entry, X, started)
    return Explanation(
        **prediction.model_dump(),
        base_log_odds=base,
        log_odds=base + float(per_feature.sum()),
        contributions=contributions,
    )
