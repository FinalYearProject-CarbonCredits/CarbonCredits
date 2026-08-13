"""Biomass to carbon stock conversion (configurable, clearly labelled)."""

from typing import Any

# IPCC-style range for above-ground woody biomass; default mid-point
DEFAULT_CARBON_FRACTION = 0.47
CO2_MOLAR_RATIO = 44 / 12


def biomass_to_carbon(
    mean_agbd: float,
    area_ha: float,
    carbon_fraction: float = DEFAULT_CARBON_FRACTION,
) -> dict[str, Any]:
    """
    Convert parcel-level AGBD to biomass, carbon stock, and CO2e.

    AGBD is in Mg/ha (metric tonnes biomass per hectare).
    Total biomass (Mg) = mean_agbd × area_ha
    Carbon stock (Mg C) = biomass × carbon_fraction
    CO2e (Mg) = carbon × 44/12
    """
    total_biomass_mg = round(mean_agbd * area_ha, 2)
    carbon_stock_mgc = round(total_biomass_mg * carbon_fraction, 2)
    co2e_mg = round(carbon_stock_mgc * CO2_MOLAR_RATIO, 2)

    return {
        "total_biomass_mg": total_biomass_mg,
        "carbon_stock_mgc": carbon_stock_mgc,
        "co2e_mg": co2e_mg,
        "co2e_tonnes": round(co2e_mg, 2),
        "carbon_fraction_used": carbon_fraction,
        "assumptions": {
            "carbon_fraction": carbon_fraction,
            "carbon_fraction_note": (
                "Default 0.47 (IPCC literature range ~0.47–0.50 for above-ground woody biomass). "
                "Configurable per assessment."
            ),
            "co2_conversion": "CO₂e = Carbon (Mg) × 44/12",
            "not_carbon_credits": True,
            "disclaimer": (
                "Estimated carbon stock from satellite/ML biomass — NOT verified carbon credits."
            ),
        },
    }
