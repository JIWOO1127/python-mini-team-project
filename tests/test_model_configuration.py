import json
from pathlib import Path

from src.ml.model_adapter import manifest, random_vehicle_id, validate_bundle, vehicles
from src.providers.registry import settings


def test_active_model_is_defined_by_manifest():
    current = validate_bundle()

    assert current["version"] == "lightgbm-ver2"
    assert settings().get("active_model") is None
    assert manifest()["version"] == current["version"]


def test_manifest_references_existing_runtime_files():
    current = json.loads(
        Path("models/model_manifest.json").read_text(encoding="utf-8")
    )

    assert current["model_path"] == "models/lightgbm-ver2/lgbm_battery_model.pkl"
    assert current["test_data_path"] == "data/test/lightgbm-ver2/vehicles.csv"
    assert current["feature_profile_path"] == "data/test/lightgbm-ver2/feature_profile.json"


def test_random_vehicle_id_comes_from_active_test_dataset():
    selected = random_vehicle_id()
    ids = set(vehicles()["vehicle_id"].dropna().astype(str).str.strip())

    assert selected in ids
    assert selected
