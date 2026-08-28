import pandas as pd
import pytest

from src.ml import predictor


def make_values():
    return {column: index for index, column in enumerate(predictor.FINAL_COLS)}


def test_model_path_uses_received_pickle():
    assert predictor.MODEL_PATH.name == "battery_failure_model.pkl"


def test_build_model_input_uses_float_final_column_order():
    model_input = predictor.build_model_input(make_values())
    assert model_input.columns.tolist() == predictor.FINAL_COLS
    assert model_input.shape == (1, len(predictor.FINAL_COLS))
    assert all(dtype.kind == "f" for dtype in model_input.dtypes)


def test_build_model_input_rejects_missing_column():
    values = make_values()
    values.pop("manufacturing_year")
    with pytest.raises(ValueError, match="manufacturing_year"):
        predictor.build_model_input(values)


def test_load_vehicle_needs_no_brand_and_fills_missing_value(
    tmp_path, monkeypatch,
):
    first = {"vehicle_id": "EV0001", **make_values()}
    first["manufacturing_year"] = None
    second = {"vehicle_id": "EV0002", **make_values()}
    second["manufacturing_year"] = 2022
    csv_path = tmp_path / "vehicles.csv"
    pd.DataFrame([first, second]).to_csv(csv_path, index=False)
    monkeypatch.setattr(predictor, "VEHICLE_DATA_PATH", csv_path)

    vehicle = predictor.load_vehicle("ev0001")

    assert vehicle["vehicle_id"] == "EV0001"
    assert vehicle["model_input"].iloc[0]["manufacturing_year"] == 2022


def test_status_uses_failure_label_convention():
    assert predictor._status_for_label(0) == "normal"
    assert predictor._status_for_label(1) == "abnormal"


class ProbabilityModel:
    classes_ = [0, 1]

    def predict_proba(self, model_input):
        return [[0.25, 0.75]]


def test_failure_probability_returns_class_one_probability():
    probability = predictor._failure_probability(
        ProbabilityModel(), predictor.build_model_input(make_values())
    )
    assert probability == 0.75
