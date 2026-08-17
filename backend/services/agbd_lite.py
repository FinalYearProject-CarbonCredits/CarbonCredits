"""AGBD-Lite v2: trained Random Forest on GEDI + Sentinel-2 features.

When GEDI footprints are missing inside a parcel, biomass is inferred from
Sentinel-2 NDVI/EVI (and optional nearby GEDI as a calibration feature)
using a Random Forest trained on GEDI-calibrated samples. Falls back to
the original NDVI power-law if the model file is missing.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

import numpy as np

MODEL_NAME = "AGBD-Lite"
MODEL_VERSION = "2.0.0-rf-gedi-sentinel"
MODEL_PATH = Path(__file__).resolve().parent / "agbd_lite_model.json"

MIN_NDVI = 0.15
MAX_AGBD = 350.0
MIN_AGBD = 5.0

FEATURE_NAMES = [
    "ndvi",
    "evi",
    "ndvi_sq",
    "evi_sq",
    "ndvi_evi",
    "ndvi_std",
    "nearby_gedi",
    "has_nearby_gedi",
]


@lru_cache(maxsize=1)
def _load_model() -> dict[str, Any] | None:
    if not MODEL_PATH.exists():
        return None
    try:
        return json.loads(MODEL_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def _predict_tree(node: dict, x: np.ndarray) -> float:
    while node.get("l") is not None:
        node = node["l"] if float(x[node["f"]]) <= float(node["t"]) else node["r"]
    return float(node["v"])


def _predict_rf(model: dict, x: np.ndarray) -> float:
    trees = model["trees"]
    return sum(_predict_tree(t, x) for t in trees) / len(trees)


def _power_law_ndvi(ndvi_mean: float) -> float:
    adjusted = max(ndvi_mean - 0.1, 0.05)
    return min(MAX_AGBD, max(MIN_AGBD, 250.0 * (adjusted ** 2.5)))


def _feature_vector(
    ndvi_mean: float,
    evi_mean: float | None,
    ndvi_std: float | None,
    nearby_gedi_mean: float | None,
) -> np.ndarray:
    evi = float(evi_mean) if evi_mean is not None else float(ndvi_mean) * 0.65
    std = float(ndvi_std) if ndvi_std is not None else 0.08
    has_gedi = nearby_gedi_mean is not None and nearby_gedi_mean > 0
    nearby = float(nearby_gedi_mean) if has_gedi else 0.0
    return np.array(
        [
            ndvi_mean,
            evi,
            ndvi_mean * ndvi_mean,
            evi * evi,
            ndvi_mean * evi,
            std,
            nearby,
            1.0 if has_gedi else 0.0,
        ],
        dtype=np.float64,
    )


def infer_agbd_from_features(
    ndvi_mean: float,
    evi_mean: float | None = None,
    ndvi_std: float | None = None,
    nearby_gedi_mean: float | None = None,
) -> dict[str, Any]:
    """
    Infer mean AGBD (Mg/ha) from Sentinel-2 features, optionally calibrated
    with nearby GEDI L4A mean. Labelled as model inference — not in-parcel lidar.
    """
    if ndvi_mean is None or ndvi_mean < MIN_NDVI:
        return {
            "mean_agbd": None,
            "median_agbd": None,
            "min_agbd": None,
            "max_agbd": None,
            "agbd_uncertainty": None,
            "method": MODEL_NAME,
            "model_version": MODEL_VERSION,
            "available": False,
            "note": (
                f"NDVI too low ({ndvi_mean}) for biomass inference — "
                "likely non-vegetated or sparse cover."
            ),
        }

    model = _load_model()
    used_rf = model is not None and model.get("trees")
    if used_rf:
        x = _feature_vector(ndvi_mean, evi_mean, ndvi_std, nearby_gedi_mean)
        mean = float(_predict_rf(model, x))
        method_label = "AGBD-Lite RF (GEDI-calibrated Sentinel features)"
        model_reference = (
            f"Random Forest ({model.get('n_estimators')} trees) trained on "
            "GEDI L4A-style AGBD labels + Sentinel-2 NDVI/EVI features"
        )
        version = model.get("model_version", MODEL_VERSION)
        test_r2 = (model.get("test_metrics") or {}).get("r2")
        # Uncertainty: GEDI residual + RF hold-out RMSE, wider without nearby GEDI
        rmse = float((model.get("test_metrics") or {}).get("rmse_mg_ha") or 25.0)
        extra = 0.12 if nearby_gedi_mean else 0.22
        uncertainty_pct = min(0.45, rmse / max(mean, 1.0) + extra)
        # Partial pooling: nearby GEDI L4A is a stronger local prior than Sentinel-only RF
        if nearby_gedi_mean:
            mean = 0.45 * mean + 0.55 * float(nearby_gedi_mean)
    else:
        mean = _power_law_ndvi(ndvi_mean)
        method_label = "AGBD-Lite NDVI power-law (model file missing)"
        model_reference = "NDVI power-law fallback — train with scripts/train_agbd_lite.py"
        version = "1.0.0-ndvi-regression"
        test_r2 = None
        uncertainty_pct = 0.30

    mean = min(MAX_AGBD, max(MIN_AGBD, mean))
    spread = mean * uncertainty_pct

    note_bits = [
        f"AGBD inferred via {method_label}.",
        "Not in-parcel GEDI lidar — screening estimate; field plots required for issuance.",
    ]
    if nearby_gedi_mean:
        note_bits.append(f"Calibrated with nearby GEDI mean {round(nearby_gedi_mean, 1)} Mg/ha.")
    if test_r2 is not None:
        note_bits.append(f"Hold-out R²={test_r2}.")

    return {
        "mean_agbd": round(mean, 2),
        "median_agbd": round(mean, 2),
        "min_agbd": round(max(MIN_AGBD, mean - spread), 2),
        "max_agbd": round(min(MAX_AGBD, mean + spread), 2),
        "agbd_uncertainty": round(spread, 2),
        "method": MODEL_NAME,
        "model_version": version,
        "available": True,
        "used_random_forest": bool(used_rf),
        "features_used": {
            "ndvi_mean": round(float(ndvi_mean), 4),
            "evi_mean": round(float(evi_mean), 4) if evi_mean is not None else None,
            "ndvi_std": round(float(ndvi_std), 4) if ndvi_std is not None else None,
            "nearby_gedi_mean": round(float(nearby_gedi_mean), 2) if nearby_gedi_mean else None,
        },
        "note": " ".join(note_bits),
        "model_reference": model_reference,
    }


def infer_agbd_from_ndvi(ndvi_mean: float, **kwargs: Any) -> dict[str, Any]:
    """Backward-compatible wrapper — prefers multi-feature inference when kwargs given."""
    return infer_agbd_from_features(ndvi_mean, **kwargs)
