from unittest.mock import patch

from src.services.diagnosis import diagnose


@patch("src.services.diagnosis.top_risk_factors", return_value=[
    {"feature": "thermal_runaway_risk", "severity": 80.0},
])
@patch("src.services.diagnosis.predict_vehicle", return_value={
    "vehicle_id": "EV0001",
    "brand": "Tesla",
    "status": "normal",
    "prediction": "0",
    "probability": 0.1,
    "row": {"thermal_runaway_risk": 0.8},
})
def test_diagnose_uses_active_model_adapter(mock_predict, mock_risks):
    result = diagnose("EV0001")

    assert result["vehicle_id"] == "EV0001"
    assert result["status"] == "normal"
    assert result["risk_factors"][0]["feature"] == "thermal_runaway_risk"
    mock_predict.assert_called_once_with("EV0001")
    mock_risks.assert_called_once_with({"thermal_runaway_risk": 0.8})
