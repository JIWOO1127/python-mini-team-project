from __future__ import annotations

from src.ml.model_adapter import manifest, profile


def _severity(value: float, stats: dict, direction: str) -> float:
    median = float(stats.get("p50", value))
    extreme = float(stats.get("p90" if direction == "high" else "p10", value))
    if direction == "high":
        denominator = max(extreme - median, 1e-9)
        return max(0.0, min(1.0, (value - median) / denominator))
    denominator = max(median - extreme, 1e-9)
    return max(0.0, min(1.0, (median - value) / denominator))


def top_risk_factors(vehicle_row: dict, limit: int = 3) -> list[dict]:
    statistics = profile().get("features", {})
    factors = []
    for feature in manifest().get("risk_features", []):
        name = feature["name"]
        raw_value = vehicle_row.get(name)
        try:
            value = float(raw_value)
        except (TypeError, ValueError):
            continue
        score = _severity(value, statistics.get(name, {}), feature["direction"])
        display_value = value * 100 if name == "fast_charge_ratio" else value
        factors.append({"feature": name, "label": feature["label"], "value": round(display_value, 2), "unit": feature["unit"], "severity": round(score * 100, 1)})
    return sorted(factors, key=lambda item: item["severity"], reverse=True)[:limit]
