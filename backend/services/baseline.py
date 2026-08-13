"""Baseline, additionality, leakage, and buffer modelling for preliminary credit estimates."""

from typing import Any

# Business-as-usual annual sequestration (tCO2e/ha/yr) without project intervention
BASELINE_RATES = {
    "mangrove": 0.5,
    "forest": 0.3,
    "reforestation": 0.2,
    "wetland": 0.2,
    "scrub": 0.1,
    "default": 0.15,
}

DEFAULT_LEAKAGE_PCT = 10.0
DEFAULT_BUFFER_PCT = 15.0


def assess_baseline_additionality(
    area_ha: float,
    land_classification: str,
    annual_removal_min: float,
    annual_removal_max: float,
    project_duration_years: int = 20,
    leakage_pct: float = DEFAULT_LEAKAGE_PCT,
    buffer_pct: float = DEFAULT_BUFFER_PCT,
    kyc_verified: bool = False,
    land_verified: bool = False,
) -> dict[str, Any]:
    """
    Compute preliminary baseline, additionality, and net creditable removal range.
    NOT verified carbon credits — screening model only.
    """
    baseline_rate = BASELINE_RATES.get(land_classification, BASELINE_RATES["default"])
    baseline_annual = round(area_ha * baseline_rate, 2)
    baseline_total = round(baseline_annual * project_duration_years, 1)

    additionality_annual_min = round(max(0, annual_removal_min - baseline_annual), 2)
    additionality_annual_max = round(max(0, annual_removal_max - baseline_annual), 2)
    additionality_total_min = round(additionality_annual_min * project_duration_years, 1)
    additionality_total_max = round(additionality_annual_max * project_duration_years, 1)

    leakage_factor = 1.0 - (leakage_pct / 100.0)
    buffer_factor = 1.0 - (buffer_pct / 100.0)
    net_factor = leakage_factor * buffer_factor

    net_annual_min = round(additionality_annual_min * net_factor, 2)
    net_annual_max = round(additionality_annual_max * net_factor, 2)
    net_total_min = round(additionality_total_min * net_factor, 1)
    net_total_max = round(additionality_total_max * net_factor, 1)

    # Additionality score 0–100 for screening (higher = more additional removal vs baseline)
    if annual_removal_max > 0:
        add_score = min(100, round((additionality_annual_max / annual_removal_max) * 100, 1))
    else:
        add_score = 0.0

    verification_readiness = []
    if kyc_verified:
        verification_readiness.append("KYC verified offline")
    else:
        verification_readiness.append("KYC pending — required for verified credits path")
    if land_verified:
        verification_readiness.append("Land document verified offline")
    else:
        verification_readiness.append("Land verification pending")

    return {
        "status": "PRELIMINARY_BASELINE",
        "land_classification": land_classification,
        "baseline_annual_tco2e_ha": baseline_rate,
        "baseline_annual_tco2e": baseline_annual,
        "baseline_total_tco2e": baseline_total,
        "additionality_annual_tco2e": {"min": additionality_annual_min, "max": additionality_annual_max},
        "additionality_total_tco2e": {"min": additionality_total_min, "max": additionality_total_max},
        "additionality_score_pct": add_score,
        "leakage_deduction_pct": leakage_pct,
        "buffer_pool_pct": buffer_pct,
        "net_creditable_annual_tco2e": {"min": net_annual_min, "max": net_annual_max},
        "net_creditable_total_tco2e": {"min": net_total_min, "max": net_total_max},
        "verification_readiness": verification_readiness,
        "disclaimer": (
            "Preliminary baseline and additionality screening — not methodology-approved MRV. "
            "Third-party validation required before registry issuance."
        ),
    }
