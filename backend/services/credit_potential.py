"""Preliminary carbon credit potential estimation — NOT verified issuance."""

from typing import Any

from services.baseline import assess_baseline_additionality

# Conservative annual sequestration rates by land type (tCO2e/ha/yr) — literature-informed ranges
SEQUESTRATION_RATES = {
    "mangrove": (3.0, 8.0),
    "reforestation": (2.0, 6.0),
    "forest": (1.5, 5.0),
    "wetland": (1.0, 4.0),
    "scrub": (0.5, 2.0),
    "default": (1.0, 3.0),
}


def classify_land_from_ndvi(ndvi: float | None) -> str:
    if ndvi is None:
        return "default"
    if ndvi >= 0.65:
        return "forest"
    if ndvi >= 0.45:
        return "reforestation"
    if ndvi >= 0.30:
        return "scrub"
    return "default"


def estimate_credit_potential(
    area_ha: float,
    ndvi_mean: float | None = None,
    mean_agbd: float | None = None,
    carbon_stock_mgc: float | None = None,
    project_duration_years: int = 20,
    land_type: str | None = None,
    kyc_verified: bool = False,
    land_verified: bool = False,
) -> dict[str, Any]:
    """
    Estimate PRELIMINARY carbon credit potential.
    This is NOT verified carbon credit issuance.
    """
    land = land_type or classify_land_from_ndvi(ndvi_mean)
    rate_min, rate_max = SEQUESTRATION_RATES.get(land, SEQUESTRATION_RATES["default"])

    # Scale by vegetation health when NDVI available
    if ndvi_mean is not None:
        factor = min(max(ndvi_mean / 0.6, 0.3), 1.2)
        rate_min *= factor
        rate_max *= factor

    annual_min = round(area_ha * rate_min, 1)
    annual_max = round(area_ha * rate_max, 1)
    total_min = round(annual_min * project_duration_years, 0)
    total_max = round(annual_max * project_duration_years, 0)

    baseline = assess_baseline_additionality(
        area_ha=area_ha,
        land_classification=land,
        annual_removal_min=annual_min,
        annual_removal_max=annual_max,
        project_duration_years=project_duration_years,
        kyc_verified=kyc_verified,
        land_verified=land_verified,
    )

    return {
        "status": "PRELIMINARY_ESTIMATE",
        "verified": False,
        "disclaimer": (
            "Preliminary estimate of potential carbon removal — NOT verified carbon credits. "
            "Actual creditable quantity requires KYC, methodology selection, baseline study, "
            "additionality proof, third-party verification, and registry issuance."
        ),
        "land_classification": land,
        "project_duration_years": project_duration_years,
        "estimated_annual_removal_tco2e": {"min": annual_min, "max": annual_max},
        "estimated_total_potential_tco2e": {"min": total_min, "max": total_max},
        "existing_carbon_stock_mgc": carbon_stock_mgc,
        "mean_agbd_mg_ha": mean_agbd,
        "baseline_assessment": baseline,
        "net_creditable_annual_tco2e": baseline["net_creditable_annual_tco2e"],
        "net_creditable_total_tco2e": baseline["net_creditable_total_tco2e"],
        "additionality_score_pct": baseline["additionality_score_pct"],
        "methodology_notes": baseline["disclaimer"],
        "next_steps": [
            "Complete offline KYC verification" if not kyc_verified else "KYC verified — proceed to methodology",
            "Complete land document verification" if not land_verified else "Land verified — proceed to MRV design",
            "Select carbon methodology (e.g. AR-ACM0003, VM0033)",
            "Third-party validation and registry registration",
        ],
    }
