"""
Data Ingestion Package
======================
Loaders for 15-minute interval energy telemetry and building metadata.
"""

from .pecan_loader import load_raw_energy_data, load_household_metadata

__all__ = ["load_raw_energy_data", "load_household_metadata"]
