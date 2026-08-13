#!/usr/bin/env python3
"""
GEDI L4A validation script — Phase 6 sanity check.

Usage:
    cd backend
    python scripts/validate_gedi.py
    python scripts/validate_gedi.py --bbox 72.9 19.2 73.0 19.25
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from services.gedi import fetch_gedi_footprints_in_bbox, fetch_gedi_via_ornl_subset, summarize_gedi_agbd

# Sanjay Gandhi National Park approximate bbox
DEFAULT_BBOX = (72.88, 19.15, 73.05, 19.28)


def validate_bbox(bbox: tuple[float, float, float, float]) -> dict:
    print(f"Querying GEDI L4A for bbox {bbox}...")
    footprints = fetch_gedi_footprints_in_bbox(bbox, limit=100)
    source = "LP DAAC CMR"

    if not footprints:
        print("  LP DAAC returned 0 — trying ORNL fallback...")
        footprints = fetch_gedi_via_ornl_subset(bbox)
        source = "ORNL subset"

    summary = summarize_gedi_agbd(footprints)
    result = {
        "bbox": bbox,
        "source": source,
        "footprint_count": summary["count"],
        "mean_agbd": summary["mean_agbd"],
        "median_agbd": summary["median_agbd"],
        "min_agbd": summary["min_agbd"],
        "max_agbd": summary["max_agbd"],
        "status": "PASS" if summary["count"] >= 1 else "NO_COVERAGE",
    }

    print(json.dumps(result, indent=2))
    if summary["count"] == 0:
        print("\nNo GEDI footprints — AGBD-Lite NDVI fallback will be used for parcel analysis.")
        return result

    print(f"\n{summary['count']} footprints found — GEDI direct AGBD available.")
    return result


def main():
    parser = argparse.ArgumentParser(description="Validate GEDI L4A coverage for a bbox")
    parser.add_argument("--bbox", nargs=4, type=float, metavar=("MIN_LON", "MIN_LAT", "MAX_LON", "MAX_LAT"))
    args = parser.parse_args()

    bbox = tuple(args.bbox) if args.bbox else DEFAULT_BBOX
    validate_bbox(bbox)


if __name__ == "__main__":
    main()
