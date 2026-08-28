"""Train a runtime-compatible default model while keeping test vehicle IDs held out."""

from __future__ import annotations

import json
import os
from pathlib import Path

import joblib
import pandas as pd
from xgboost import XGBClassifier


ROOT = Path(__file__).resolve().parents[1]


def resolve_source() -> Path:
    """Prefer the share-package raw-data location, with legacy fallback."""
    configured = os.getenv("EV_SOURCE_DATA_PATH")
    if configured:
        return Path(configured)
    package_source = ROOT / "data" / "raw" / "ev_battery_failure_dataset.csv"
    return package_source if package_source.exists() else ROOT.parent / "archive" / "ev_battery_failure_dataset.csv"


SOURCE = resolve_source()
MANIFEST = ROOT / "models" / "model_manifest.json"
TEST_DATA = ROOT / "data" / "test" / "default" / "vehicles.csv"
OUTPUT = ROOT / "models" / "default" / "model.pkl"


def main() -> None:
    if not SOURCE.exists() or not TEST_DATA.exists():
        raise SystemExit("원본 데이터와 테스트 차량 번들을 먼저 준비해주세요.")
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    features = manifest["feature_columns"]
    source = pd.read_csv(SOURCE, usecols=["vehicle_id", "battery_failure", *features])
    test_ids = set(pd.read_csv(TEST_DATA, usecols=["vehicle_id"])["vehicle_id"].astype(str))
    train = source[~source["vehicle_id"].astype(str).isin(test_ids)].copy()
    medians = train[features].median(numeric_only=True)
    train[features] = train[features].fillna(medians)
    model = XGBClassifier(
        n_estimators=180, max_depth=5, learning_rate=0.08, subsample=0.85,
        colsample_bytree=0.9, eval_metric="logloss", random_state=42, n_jobs=4,
    )
    model.fit(train[features], train["battery_failure"])
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, OUTPUT)
    manifest["imputation_medians"] = {key: round(float(value), 6) for key, value in medians.items()}
    manifest["metrics"] = {"training_rows": int(len(train)), "held_out_vehicle_count": int(len(test_ids)), "note": "기본 XGBoost 모델은 테스트 차량 ID를 학습에서 제외했습니다."}
    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Trained {len(train):,} rows and saved {OUTPUT}")


if __name__ == "__main__":
    main()
