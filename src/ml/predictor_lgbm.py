"""Load vehicle rows and run the battery failure model."""

from pathlib import Path

import joblib
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]
MODEL_PATH = PROJECT_ROOT / "models" / "lgbm_battery_model.pkl"
VEHICLE_DATA_PATH = PROJECT_ROOT / "data" / "vehicle_samples" / "vehicles_lgbm.csv"

FINAL_COLS = [
    "capacity_loss_percent", "charge_efficiency", "cycle_count",
    "voltage_imbalance", "charging_quality_score", "thermal_runaway_risk",
    "internal_resistance", "daily_distance", "charging_cycles_last_month",
    "remaining_capacity", "battery_stress_index", "cooling_system_health",
    "fast_charge_ratio", "BMS_warning_count", "vehicle_age_years",
]


def build_model_input(values):
    """Build a one-row float DataFrame in the training-column order."""
    missing = [column for column in FINAL_COLS if column not in values]
    if missing:
        raise ValueError(f"모델 입력값이 부족합니다: {', '.join(missing)}")
    return pd.DataFrame(
        [[values[column] for column in FINAL_COLS]],
        columns=FINAL_COLS,
        dtype=float,
    )


def load_vehicle(vehicle_id):
    """Find one vehicle and prepare its model input."""
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

    row = matches.iloc[0].copy()
    # 변경 후 (imputer는 predict_vehicle에서 적용하므로 여기선 raw 값만 반환)
    return {
        "vehicle_id": str(row["vehicle_id"]).strip(),
        "model_input": build_model_input(row.to_dict()),
    }


# 변경 후
def load_model():
    if not MODEL_PATH.exists():
        raise FileNotFoundError(f"통합 모델 파일이 없습니다: {MODEL_PATH.name}")
    artifact = joblib.load(MODEL_PATH)
    return artifact   # {'model', 'imputer', 'features', 'threshold'}


def _status_for_label(label):
    """Map the training label (0=normal, 1=failure) to API status."""
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


# 변경 후
def predict_vehicle(vehicle_id):
    vehicle = load_vehicle(vehicle_id)
    artifact = load_model()
    model     = artifact['model']
    imputer   = artifact['imputer']
    threshold = artifact['threshold']   # 0.2

    if not hasattr(model, "predict"):
        raise TypeError("모델에 predict 함수가 없습니다.")

    # 결측 보정 (학습 데이터 기준 고정값)
    model_input = pd.DataFrame(
        imputer.transform(vehicle["model_input"]),
        columns=FINAL_COLS
    )

    # 확률 기반 판정 (임계값 0.2)
    probability = _failure_probability(model, model_input)
    if probability is not None:
        prediction = 1 if probability >= threshold else 0
    else:
        prediction = model.predict(model_input)[0]

    return {
        "vehicle_id": vehicle["vehicle_id"],
        "prediction": str(prediction),
        "status": _status_for_label(prediction),
        "probability": probability,
    }
