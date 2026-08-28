from __future__ import annotations

import json
import secrets
from functools import lru_cache
from pathlib import Path

import joblib
import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
MANIFEST_PATH = ROOT / "models" / "model_manifest.json"


class ModelBundleError(RuntimeError):
    pass


_REQUIRED_MANIFEST_KEYS = {
    "version",
    "model_type",
    "model_path",
    "test_data_path",
    "feature_profile_path",
    "feature_columns",
    "threshold",
}


@lru_cache(maxsize=1)
def manifest() -> dict:
    if not MANIFEST_PATH.exists():
        raise ModelBundleError("모델 메타데이터 파일을 찾을 수 없습니다.")
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


def validate_bundle() -> dict:
    """Validate the active model manifest and all referenced runtime files."""
    current = manifest()
    missing_keys = sorted(_REQUIRED_MANIFEST_KEYS.difference(current))
    if missing_keys:
        raise ModelBundleError(
            f"모델 manifest 필수 항목이 없습니다: {', '.join(missing_keys)}"
        )
    if not isinstance(current["feature_columns"], list) or not current["feature_columns"]:
        raise ModelBundleError("모델 manifest의 feature_columns가 비어 있습니다.")
    for key in ("model_path", "test_data_path", "feature_profile_path"):
        path = ROOT / current[key]
        if not path.exists():
            raise ModelBundleError(f"manifest 참조 파일을 찾을 수 없습니다: {path}")
    vehicle_data = vehicles()
    feature_profile = profile()
    profile_features = feature_profile.get("features") if isinstance(feature_profile, dict) else None
    if not isinstance(profile_features, dict):
        raise ModelBundleError("모델 feature profile의 features 항목이 없습니다.")
    missing_profile = sorted(set(current["feature_columns"]) - set(profile_features))
    if missing_profile:
        raise ModelBundleError(
            f"feature profile 컬럼이 부족합니다: {', '.join(missing_profile)}"
        )
    missing_csv = sorted(set(current["feature_columns"]) - set(vehicle_data.columns))
    if missing_csv:
        raise ModelBundleError(
            f"차량 CSV 피처 컬럼이 부족합니다: {', '.join(missing_csv)}"
        )
    return current


@lru_cache(maxsize=1)
def artifact():
    path = ROOT / manifest()["model_path"]
    if not path.exists():
        raise ModelBundleError(f"모델 파일을 찾을 수 없습니다: {path.name}")
    return joblib.load(path)


@lru_cache(maxsize=1)
def model():
    loaded = artifact()
    return loaded["model"] if isinstance(loaded, dict) and "model" in loaded else loaded


@lru_cache(maxsize=1)
def vehicles() -> pd.DataFrame:
    path = ROOT / manifest()["test_data_path"]
    if not path.exists():
        raise ModelBundleError("테스트 차량 데이터가 준비되지 않았습니다.")
    data = pd.read_csv(path, encoding="utf-8-sig")
    required = {"vehicle_id", *manifest()["feature_columns"]}
    missing = sorted(required.difference(data.columns))
    if missing:
        raise ModelBundleError(f"차량 CSV 컬럼이 부족합니다: {', '.join(missing)}")
    return data


@lru_cache(maxsize=1)
def vehicle_metadata() -> pd.DataFrame:
    path_value = manifest().get("metadata_data_path")
    if not path_value:
        return pd.DataFrame()
    path = ROOT / path_value
    if not path.exists():
        return pd.DataFrame()
    data = pd.read_csv(path, encoding="utf-8-sig")
    return data.drop_duplicates(subset=["vehicle_id"]) if "vehicle_id" in data.columns else pd.DataFrame()


@lru_cache(maxsize=1)
def profile() -> dict:
    path = ROOT / manifest()["feature_profile_path"]
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def dashboard_metadata() -> dict:
    estimator = model()
    features = manifest()["feature_columns"]
    scores = getattr(estimator, "feature_importances_", [])
    raw = [(feature, float(score)) for feature, score in zip(features, scores)]
    maximum = max((score for _, score in raw), default=0.0)
    # LightGBM returns split counts (for example, 759), whereas the Tkinter
    # progress bar expects a 0~1 relative value. Preserve the raw score too.
    importances = sorted(
        (
            {
                "feature": feature,
                "importance": round(score / maximum, 5) if maximum else 0.0,
                "raw_importance": round(score, 5),
            }
            for feature, score in raw
        ),
        key=lambda item: item["importance"], reverse=True,
    )
    return {
        "version": manifest()["version"], "model_type": manifest()["model_type"],
        "metrics": manifest().get("metrics", {}), "feature_count": len(features),
        "feature_importance": importances[:10], "probability_available": hasattr(estimator, "predict_proba"),
    }


def _status(label) -> str:
    return manifest().get("label_mapping", {}).get(str(label).strip().lower(), "unknown")


def find_vehicle(vehicle_id: str) -> pd.Series:
    key = vehicle_id.strip().casefold()
    if not key:
        raise ValueError("차량 ID를 입력해주세요.")
    matches = vehicles()[vehicles()["vehicle_id"].astype(str).str.strip().str.casefold() == key]
    if matches.empty:
        raise LookupError("등록되지 않은 테스트 차량 ID입니다.")
    if len(matches) > 1:
        raise ValueError("테스트 차량 ID가 중복되어 있습니다.")
    return matches.iloc[0]


def random_vehicle_id() -> str:
    """Return a non-empty, randomly selected ID from the active test bundle."""
    ids = vehicles()["vehicle_id"].dropna().astype(str).str.strip()
    candidates = list(dict.fromkeys(vehicle_id for vehicle_id in ids if vehicle_id))
    if not candidates:
        raise ModelBundleError("테스트 차량 데이터에 사용할 차량 ID가 없습니다.")
    return secrets.choice(candidates)


def _summary(row: pd.Series) -> dict:
    fields = [
        "vehicle_brand", "vehicle_model", "battery_chemistry", "odometer_km",
        "battery_health_percent", "cycle_count", "charging_quality_score",
        "internal_resistance", "capacity_loss_percent",
    ]
    values = row.to_dict()
    meta = vehicle_metadata()
    if not meta.empty:
        matches = meta[meta["vehicle_id"].astype(str).str.strip().str.casefold() == str(row["vehicle_id"]).strip().casefold()]
        if not matches.empty:
            values.update(matches.iloc[0].to_dict())
    return {field: None if pd.isna(values.get(field)) else values.get(field) for field in fields}


def predict_vehicle(vehicle_id: str) -> dict:
    row = find_vehicle(vehicle_id).copy()
    features = manifest()["feature_columns"]
    data = vehicles()
    for feature in features:
        value = pd.to_numeric(row[feature], errors="coerce")
        if pd.isna(value):
            row[feature] = pd.to_numeric(data[feature], errors="coerce").median()
    model_input = pd.DataFrame([[row[feature] for feature in features]], columns=features, dtype=float)
    loaded = artifact()
    estimator = model()
    if isinstance(loaded, dict) and loaded.get("imputer") is not None:
        model_input = pd.DataFrame(loaded["imputer"].transform(model_input), columns=features)
    if not hasattr(estimator, "predict"):
        raise ModelBundleError("모델이 predict 인터페이스를 지원하지 않습니다.")
    probability = None
    if hasattr(estimator, "predict_proba"):
        probability = float(estimator.predict_proba(model_input)[0][1])
    label = 1 if probability is not None and probability >= float(manifest().get("threshold", 0.5)) else estimator.predict(model_input)[0]
    summary = _summary(row)
    return {
        "vehicle_id": str(row["vehicle_id"]), "brand": str(summary.get("vehicle_brand") or "Tesla"),
        "status": _status(label), "prediction": str(label), "probability": probability,
        "row": row.to_dict(), "vehicle_summary": summary,
    }
