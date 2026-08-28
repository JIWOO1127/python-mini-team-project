from __future__ import annotations

from src.ml.model_adapter import dashboard_metadata, predict_vehicle, random_vehicle_id
from src.services.risk_factors import top_risk_factors


def diagnose(vehicle_id: str) -> dict:
    result = predict_vehicle(vehicle_id)
    result["risk_factors"] = top_risk_factors(result.pop("row"))
    return result


def dashboard() -> dict:
    metadata = dashboard_metadata()
    return {
        "model": metadata,
        "notice": "합성 데이터 기반의 참고용 결과이며 실제 정비 확정 판정이 아닙니다.",
        "eda": {
            "dataset": "EV Battery Failure Prediction Dataset",
            "rows": 200000,
            "columns": 70,
            "failure_rate": 9.96,
            "summary": "배터리 건강도, 용량 손실, 노화·열 위험 지표를 중심으로 고장 위험을 분석합니다.",
        },
        "sample_vehicle_id": random_vehicle_id(),
    }


def sample_vehicle() -> dict:
    """Return a fresh random vehicle ID from the active test dataset."""
    return {"vehicle_id": random_vehicle_id()}
