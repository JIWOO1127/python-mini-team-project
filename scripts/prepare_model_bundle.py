"""Create a versioned test-vehicle bundle without copying the raw training dataset."""

from __future__ import annotations

import json
import os
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]


def resolve_source() -> Path:
    """Prefer the share-package raw-data location, with legacy fallback."""
    configured = os.getenv("EV_SOURCE_DATA_PATH")
    if configured:
        return Path(configured)
    package_source = ROOT / "data" / "raw" / "ev_battery_failure_dataset.csv"
    return package_source if package_source.exists() else ROOT.parent / "archive" / "ev_battery_failure_dataset.csv"


SOURCE = resolve_source()
INPUT = ROOT / "data" / "vehicle_samples" / "vehicles.csv"
OUTPUT = ROOT / "data" / "test" / "default" / "vehicles.csv"
PROFILE = ROOT / "data" / "test" / "default" / "feature_profile.json"
MANIFEST = ROOT / "models" / "model_manifest.json"


def main() -> None:
    if not SOURCE.exists():
        raise SystemExit(f"원본 데이터를 찾을 수 없습니다: {SOURCE}")
    features = json.loads(MANIFEST.read_text(encoding="utf-8"))["feature_columns"]
    test_rows = pd.read_csv(INPUT, encoding="utf-8-sig")
    metadata = pd.read_csv(SOURCE, usecols=["vehicle_id", "vehicle_brand", "vehicle_model", "battery_chemistry"])
    result = test_rows.merge(metadata, on="vehicle_id", how="left", validate="one_to_one")
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(OUTPUT, index=False, encoding="utf-8-sig")
    profile = {"features": {}}
    for feature in features:
        values = pd.to_numeric(result[feature], errors="coerce").dropna()
        profile["features"][feature] = {"p10": round(float(values.quantile(.1)), 6), "p50": round(float(values.quantile(.5)), 6), "p90": round(float(values.quantile(.9)), 6)}
    PROFILE.write_text(json.dumps(profile, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Prepared {len(result):,} test vehicles at {OUTPUT}")


if __name__ == "__main__":
    main()
