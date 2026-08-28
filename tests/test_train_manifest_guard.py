import hashlib
import json

import pandas as pd

from scripts import train_default_model


def test_training_writes_isolated_bundle_without_changing_active_manifest(tmp_path, monkeypatch):
    active_manifest = {
        "version": "lightgbm-ver2",
        "model_type": "LightGBM classifier (ver2)",
        "model_path": "models/lightgbm-ver2/lgbm_battery_model.pkl",
        "test_data_path": "data/test/lightgbm-ver2/vehicles.csv",
        "feature_profile_path": "data/test/lightgbm-ver2/feature_profile.json",
        "feature_columns": ["f1", "f2"],
        "label_mapping": {"0": "normal", "1": "abnormal"},
        "threshold": 0.2,
    }
    active_path = tmp_path / "active_manifest.json"
    active_path.write_text(json.dumps(active_manifest), encoding="utf-8")
    source_path = tmp_path / "source.csv"
    test_path = tmp_path / "test.csv"
    pd.DataFrame([
        {"vehicle_id": "EV1", "battery_failure": 0, "f1": 0.0, "f2": 0.1},
        {"vehicle_id": "EV2", "battery_failure": 1, "f1": 1.0, "f2": 0.9},
        {"vehicle_id": "EV3", "battery_failure": 0, "f1": 0.1, "f2": 0.2},
    ]).to_csv(source_path, index=False)
    pd.DataFrame([{"vehicle_id": "EV3"}]).to_csv(test_path, index=False)
    output_dir = tmp_path / "generated-xgb"

    monkeypatch.setattr(train_default_model, "ACTIVE_MANIFEST", active_path)
    monkeypatch.setattr(train_default_model, "SOURCE", source_path)
    monkeypatch.setattr(train_default_model, "TEST_DATA", test_path)
    monkeypatch.setattr(train_default_model, "OUTPUT_DIR", output_dir)
    monkeypatch.setattr(train_default_model, "OUTPUT", output_dir / "model.pkl")
    monkeypatch.setattr(train_default_model, "OUTPUT_MANIFEST", output_dir / "model_manifest.json")

    before = hashlib.sha256(active_path.read_bytes()).hexdigest()
    train_default_model.main()
    after = hashlib.sha256(active_path.read_bytes()).hexdigest()

    assert before == after
    generated = json.loads((output_dir / "model_manifest.json").read_text(encoding="utf-8"))
    assert generated["version"] == "generated-xgb"
    assert (output_dir / "model.pkl").exists()
