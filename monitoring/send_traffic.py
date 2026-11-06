"""Replay the untouched test split against a running API to fill the prediction log.

Run: uv run python monitoring/send_traffic.py [--url http://localhost:8000] [--shift]
--shift simulates a changed population: credit amounts x3 and loan durations x2.
Waits on 429; for a fast demo start the API with RATE_LIMIT_PER_MINUTE=1000.
"""

import argparse
import json
import sys
import time
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "training"))
import train  # noqa: E402


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://localhost:8000")
    parser.add_argument("--shift", action="store_true")
    args = parser.parse_args()

    X, y = train.load_data()
    _, X_test, _, _ = train.split(X, y)
    if args.shift:
        X_test = X_test.assign(credit_amount=X_test.credit_amount * 3, duration=X_test.duration * 2)

    logged = 0
    with httpx.Client(base_url=args.url, timeout=10) as client:
        for payload in json.loads(X_test.to_json(orient="records")):
            res = client.post("/predict", json=payload)
            while res.status_code == 429:  # respeta el límite de la API en vez de fallar
                time.sleep(int(res.headers["Retry-After"]) + 1)
                res = client.post("/predict", json=payload)
            res.raise_for_status()
            logged += res.json()["logged"]
    print(f"sent {len(X_test)} predictions, logged {logged}")


if __name__ == "__main__":
    main()
