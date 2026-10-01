"""
Pecan Street Energy Data & Household Metadata Loader
=====================================================
Ingests 15-minute interval telemetry records and household building metadata.
"""

from pathlib import Path
from typing import Optional, Tuple
import pandas as pd


def load_raw_energy_data(csv_path: Path) -> pd.DataFrame:
    """
    Load 15-minute interval energy telemetry data with timestamp parsing.
    """
    if not csv_path.exists():
        raise FileNotFoundError(f"Energy dataset not found: {csv_path}")
    df = pd.read_csv(csv_path, parse_dates=["local_15min"])
    return df


def load_household_metadata(metadata_path: Path) -> pd.DataFrame:
    """
    Load Pecan Street household structural and solar metadata.
    """
    if not metadata_path.exists():
        raise FileNotFoundError(f"Metadata file not found: {metadata_path}")
    return pd.read_csv(metadata_path)
