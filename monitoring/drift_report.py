"""Data-drift report: inputs logged in prediction_log vs. the training split (Evidently).

Run: uv run --group monitoring python monitoring/drift_report.py [--since 2026-11-01T00:00:00Z]
Needs DATABASE_URL. Writes reports/drift_<UTC timestamp>.html and prints the drifted columns.
"""

import os

os.environ.setdefault("DO_NOT_TRACK", "1")  # desactiva la telemetría de Evidently

import argparse  # noqa: E402
import sys  # noqa: E402
from datetime import datetime, timezone  # noqa: E402
from pathlib import Path  # noqa: E402

import pandas as pd  # noqa: E402
import psycopg  # noqa: E402
from evidently import Report  # noqa: E402
from evidently.presets import DataDriftPreset  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "training"))
import train  # noqa: E402


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--since", default="1970-01-01T00:00:00Z", help="only predictions logged after this time")
    args = parser.parse_args()

    with psycopg.connect(os.environ["DATABASE_URL"]) as conn:
        rows = conn.execute(
            "select features from prediction_log where created_at >= %s", (args.since,)
        ).fetchall()
    if not rows:
        raise SystemExit("no logged predictions in range")

    X, y = train.load_data()
    X_train, _, _, _ = train.split(X, y)
    reference = X_train.astype({c: str for c in X_train.select_dtypes("category")})
    current = pd.DataFrame([r[0] for r in rows])[reference.columns]

    snapshot = Report([DataDriftPreset()]).run(current_data=current, reference_data=reference)
    out = ROOT / "reports" / f"drift_{datetime.now(timezone.utc):%Y%m%dT%H%M%SZ}.html"
    out.parent.mkdir(exist_ok=True)
    snapshot.save_html(str(out))

    summary, *columns = snapshot.dict()["metrics"]
    print(f"current rows: {len(current)}, reference rows: {len(reference)}")
    print(f"drifted columns: {summary['value']['count']:.0f} ({summary['value']['share']:.0%})")
    for m in columns:
        cfg, value = m["config"], float(m["value"])
        # Métodos de p-value: drift si p < umbral; métodos de distancia: drift si distancia >= umbral
        drifted = value < cfg["threshold"] if "p_value" in cfg["method"] else value >= cfg["threshold"]
        if drifted:
            print(f"  {cfg['column']}: {cfg['method']} = {value:.4f} (threshold {cfg['threshold']})")
    print(f"report: {out}")


if __name__ == "__main__":
    main()
