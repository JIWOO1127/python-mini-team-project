"""Load vehicle rows and run the single battery diagnosis model."""

from pathlib import Path

import joblib
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]
MODEL_PATH = PROJECT_ROOT / "models" / "battery_failure_model.pkl"
VEHICLE_DATA_PATH = PROJECT_ROOT / "data" / "vehicle_samples" / "vehicles.csv"

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

# 한글 변수명 매핑
COL_KR = {
    "manufacturing_year":            "제조연도",
    "odometer_km":                   "주행거리(km)",
    "cycle_count":                   "충전 사이클 수",
    "battery_health_percent":        "배터리 건강도(%)",
    "internal_resistance":           "내부 저항",
    "charge_efficiency":             "충전 효율",
    "remaining_capacity":            "잔존 용량",
    "charging_cycles_last_month":    "최근 1개월 충전 횟수",
    "fast_charge_ratio":             "급속충전 비율",
    "average_trip_distance":         "평균 주행거리",
    "daily_distance":                "일일 주행거리",
    "cooling_system_health":         "냉각 시스템 건강도",
    "thermal_runaway_risk":          "열폭주 위험도",
    "voltage_imbalance":             "전압 불균형",
    "battery_stress_index":          "배터리 스트레스 지수",
    "thermal_health_score":          "열 건강 점수",
    "charging_quality_score":        "충전 품질 점수",
    "predicted_remaining_life_cycles": "예상 잔여 수명",
}

# ── 모델 캐시 (서버 시작 시 한 번만 로드) ─────────────────
_model_cache = None


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
    global _model_cache
    if _model_cache is not None:
        return _model_cache
    if not MODEL_PATH.exists():
        raise FileNotFoundError(f"통합 모델 파일이 없습니다: {MODEL_PATH.name}")
    _model_cache = joblib.load(MODEL_PATH)
    return _model_cache


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


def _top_failure_causes(model, model_input, top_n=2):
    """SHAP 기반 불량 기여 상위 변수 반환."""
    try:
        import shap
        import numpy as np
        explainer = shap.TreeExplainer(model)
        shap_values = explainer.shap_values(model_input)

        # 이진분류: shap_values가 리스트면 클래스1(불량) 선택
        if isinstance(shap_values, list):
            sv = shap_values[1][0]
        else:
            sv = shap_values[0]

        # 불량 방향(양수)만 고려
        sv_positive = [max(v, 0) for v in sv]
        total = sum(sv_positive)

        if total == 0:
            return []

        # 기여도 높은 순 정렬
        ranked = sorted(
            zip(FINAL_COLS, sv_positive),
            key=lambda x: x[1],
            reverse=True
        )[:top_n]

        return [
            {
                "feature": COL_KR.get(col, col),
                "contribution": round(val / total * 100, 1),
            }
            for col, val in ranked
            if val > 0
        ]
    except Exception:
        return []


def predict_vehicle(vehicle_id):
    """Look up a vehicle and return a normalized diagnosis payload."""
    vehicle = load_vehicle(vehicle_id)

    if not MODEL_PATH.exists():
        prediction = MOCK_PREDICTION
        probability = None
        causes = []
    else:
        model = load_model()
        if not hasattr(model, "predict"):
            raise TypeError("모델에 predict 함수가 없습니다.")
        prediction = model.predict(vehicle["model_input"])[0]
        probability = _failure_probability(model, vehicle["model_input"])
        causes = _top_failure_causes(model, vehicle["model_input"])

    return {
        "vehicle_id": vehicle["vehicle_id"],
        "vehicle_model": vehicle["vehicle_model"],
        "prediction": str(prediction),
        "status": _status_for_label(prediction),
        "probability": probability,
        "failure_causes": causes,
    }