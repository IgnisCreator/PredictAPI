"""Measure client-side latency (p50/p95/p99) of /predict and /explain under a fixed load.

Run: uv run python monitoring/load_test.py [--url http://localhost:8000] [--requests 500] [--concurrency 10]
The API's rate limit must allow the load (e.g. start it with RATE_LIMIT_PER_MINUTE=100000).
"""

import argparse
import json
import statistics
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "training"))
import train  # noqa: E402


def percentile(values, q):
    return statistics.quantiles(values, n=100, method="inclusive")[q - 1]


def run(client, endpoint, payloads, total, concurrency):
    def call(i):
        started = time.perf_counter()
        res = client.post(endpoint, json=payloads[i % len(payloads)])
        return (time.perf_counter() - started) * 1000, res.status_code

    started = time.perf_counter()
    with ThreadPoolExecutor(concurrency) as pool:
        results = list(pool.map(call, range(total)))
    elapsed = time.perf_counter() - started
    ms = [r[0] for r in results if r[1] == 200]
    errors = total - len(ms)
    print(
        f"{endpoint:9} n={total} c={concurrency} errors={errors} "
        f"p50={percentile(ms, 50):.1f}ms p95={percentile(ms, 95):.1f}ms p99={percentile(ms, 99):.1f}ms "
        f"throughput={total / elapsed:.1f} req/s"
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://localhost:8000")
    parser.add_argument("--requests", type=int, default=500)
    parser.add_argument("--concurrency", type=int, default=10)
    args = parser.parse_args()

    X, y = train.load_data()
    _, X_test, _, _ = train.split(X, y)
    payloads = json.loads(X_test.to_json(orient="records"))

    limits = httpx.Limits(max_connections=args.concurrency)
    with httpx.Client(base_url=args.url, timeout=30, limits=limits) as client:
        client.post("/predict", json=payloads[0]).raise_for_status()  # calentamiento
        for endpoint in ("/predict", "/explain"):
            run(client, endpoint, payloads, args.requests, args.concurrency)


if __name__ == "__main__":
    main()
