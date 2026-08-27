"""Load vehicle rows and run the single battery diagnosis model."""

from pathlib import Path

import joblib
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]
MODEL_PATH = PROJECT_ROOT / "models" / "battery_failure_model.pkl"
VEHICLE_DATA_PATH = PROJECT_ROOT / "data" / "vehicle_samples" / "vehicles.csv"

# Used only while the real model file is absent.
MOCK_PREDICTION = "abnormal"

FINAL_COLS = [
    "manufacturing_year", "odometer_km", "cycle_count",
    "battery_health_percent", "internal_resistance", "charge_efficiency",
    "remaining_capacity", "charging_cycles_last_month", "fast_charge_ratio",
    "average_trip_distance", "daily_distance", "cooling_system_health",
    "thermal_runaway_risk", "voltage_imbalance", "battery_stress_index",
    "thermal_health_score", "charging_quality_score",
    "predicted_remaining_life_cycles",
]


def build_model_input(values):
    """Build a one-row DataFrame in the exact training-column order."""
    missing = [column for column in FINAL_COLS if column not in values]
    if missing:
        raise ValueError(f"모델 입력값이 부족합니다: {', '.join(missing)}")
    return pd.DataFrame(
        [[values[column] for column in FINAL_COLS]], columns=FINAL_COLS,
    )


def load_vehicle(vehicle_id):
    """Find one vehicle in the UI lookup CSV, case-insensitively."""
    vehicle_id = vehicle_id.strip()
    if not vehicle_id:
        raise ValueError("차량 ID를 입력해주세요.")
    if not VEHICLE_DATA_PATH.exists():
        raise FileNotFoundError(
            f"차량 조회 CSV가 없습니다: {VEHICLE_DATA_PATH.name}"
        )

    data = pd.read_csv(VEHICLE_DATA_PATH, encoding="utf-8-sig")
    required = {"vehicle_id", *FINAL_COLS}
    missing = sorted(required.difference(data.columns))
    if missing:
        raise ValueError(f"차량 CSV 컬럼이 부족합니다: {', '.join(missing)}")

    matches = data[
        data["vehicle_id"].astype(str).str.strip().str.casefold()
        == vehicle_id.casefold()
    ]
    if matches.empty:
        raise LookupError(f"등록되지 않은 차량 ID입니다: {vehicle_id}")
    if len(matches) > 1:
        raise ValueError(f"차량 ID가 CSV에 중복되어 있습니다: {vehicle_id}")

    row = matches.iloc[0]
    return {
        "vehicle_id": str(row["vehicle_id"]).strip(),
        "vehicle_model": str(row.get("vehicle_model", "")).strip(),
        "model_input": build_model_input(row.to_dict()),
    }


def load_model():
    if not MODEL_PATH.exists():
        raise FileNotFoundError(f"통합 모델 파일이 없습니다: {MODEL_PATH.name}")
    return joblib.load(MODEL_PATH)


def _status_for_label(label):
    normalized = str(label).strip().lower()
    if normalized in {"0", "0.0", "normal"}:
        return "normal"
    if normalized in {"1", "1.0", "abnormal", "failure"}:
        return "abnormal"
    return "unknown"


def _failure_probability(model, model_input):
    """Return the probability of battery failure (class 1)."""
    if not hasattr(model, "predict_proba") or not hasattr(model, "classes_"):
        return None
    probabilities = model.predict_proba(model_input)[0]
    for index, label in enumerate(model.classes_):
        if str(label).strip() in {"1", "1.0"}:
            return float(probabilities[index])
    return None


def predict_vehicle(vehicle_id):
    """Look up a vehicle and return a normalized diagnosis payload."""
    vehicle = load_vehicle(vehicle_id)

    if not MODEL_PATH.exists():
        prediction = MOCK_PREDICTION
        probability = None
    else:
        model = load_model()
        if not hasattr(model, "predict"):
            raise TypeError("모델에 predict 함수가 없습니다.")
        prediction = model.predict(vehicle["model_input"])[0]
        probability = _failure_probability(model, vehicle["model_input"])

    return {
        "vehicle_id": vehicle["vehicle_id"],
        "vehicle_model": vehicle["vehicle_model"],
        "prediction": str(prediction),
        "status": _status_for_label(prediction),
        "probability": probability,
    }
