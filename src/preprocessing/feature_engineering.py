"""
Feature Engineering for Residential Energy Consumption
======================================================
Aggregates high-frequency 15-minute interval telemetry into monthly home consumption
and usage profiles while strictly avoiding target leakage.
"""

from typing import Dict, List, Optional
import numpy as np
import pandas as pd

# The 10 leak-free production features used across all models
MODEL_FEATURES: List[str] = [
    "season",
    "total_sqft",
    "house_age",
    "has_solar",
    "pv_size_kw",
    "building_type_code",
    "num_monitored_circuits",
    "peak_15min_kw",
    "std_consumption_kw",
    "daytime_ratio",
]

TARGET_COL: str = "house_consumption_kwh"

# Common monitored home circuit categories
CIRCUIT_COLS: List[str] = [
    "air1", "air2", "air3", "airwindowunit1", "aquarium1", "bathroom1", "bathroom2",
    "bedroom1", "bedroom2", "bedroom3", "bedroom4", "bedroom5", "battery1", "car1",
    "car2", "circpump1", "clotheswasher1", "clotheswasher_dryg1", "diningroom1",
    "diningroom2", "dishwasher1", "disposal1", "drye1", "dryg1", "freezer1",
    "furnace1", "furnace2", "garage1", "garage2", "heater1", "heater2", "heater3",
    "housefan1", "icemaker1", "jacuzzi1", "kitchen1", "kitchen2", "kitchenapp1",
    "kitchenapp2", "lights_plugs1", "lights_plugs2", "lights_plugs3", "lights_plugs4",
    "lights_plugs5", "lights_plugs6", "livingroom1", "livingroom2", "microwave1",
    "office1", "outsidelights_plugs1", "outsidelights_plugs2", "oven1", "oven2",
    "pool1", "pool2", "poollight1", "poolpump1", "pump1", "range1", "refrigerator1",
    "refrigerator2", "security1", "sewerpump1", "shed1", "sprinkler1", "sumppump1",
    "utilityroom1", "venthood1", "waterheater1", "waterheater2", "wellpump1", "winecooler1",
]


def month_to_season(month: int) -> int:
    """
    Map calendar month to meteorological season:
    0 = Spring (Mar-May), 1 = Summer (Jun-Aug), 2 = Fall (Sep-Nov), 3 = Winter (Dec-Feb).
    """
    if month in (3, 4, 5):
        return 0
    if month in (6, 7, 8):
        return 1
    if month in (9, 10, 11):
        return 2
    return 3


def aggregate_monthly_energy(df: pd.DataFrame) -> pd.DataFrame:
    """
    Aggregate 15-minute interval energy data by (dataid, year, month).
    """
    data = df.copy()
    data["year"] = data["local_15min"].dt.year
    data["month"] = data["local_15min"].dt.month
    data["hour"] = data["local_15min"].dt.hour

    # Daytime window: 06:00 to 21:59
    data["is_daytime"] = ((data["hour"] >= 6) & (data["hour"] < 22)).astype(int)
    data["season"] = data["month"].map(month_to_season)

    # Monitored circuit availability per record
    present_circuits = [c for c in CIRCUIT_COLS if c in data.columns]
    data["n_circuits_row"] = data[present_circuits].notna().sum(axis=1) if present_circuits else 0

    # Interval energy calculation: kW * 0.25h = kWh
    data["grid_kw"] = data["grid"].fillna(0).clip(lower=0)
    data["solar_kw"] = data["solar"].fillna(0).clip(lower=0)
    data["grid_kwh_interval"] = data["grid_kw"] * 0.25
    data["solar_kwh_interval"] = data["solar_kw"] * 0.25
    data["grid_kwh_daytime"] = data["grid_kwh_interval"] * data["is_daytime"]

    grp = data.groupby(["dataid", "year", "month"])
    agg = grp.agg(
        grid_consumption_kwh=("grid_kwh_interval", "sum"),
        solar_generation_kwh=("solar_kwh_interval", "sum"),
        grid_kwh_daytime=("grid_kwh_daytime", "sum"),
        peak_15min_kw=("grid_kw", "max"),
        std_consumption_kw=("grid_kw", "std"),
        season=("season", "first"),
        num_monitored_circuits=("n_circuits_row", "max"),
        n_intervals=("grid_kw", "count"),
    ).reset_index()

    agg["house_consumption_kwh"] = agg["grid_consumption_kwh"]
    agg["daytime_ratio"] = np.where(
        agg["grid_consumption_kwh"] > 0,
        (agg["grid_kwh_daytime"] / agg["grid_consumption_kwh"]).clip(0, 1),
        0.5,
    )
    agg["std_consumption_kw"] = agg["std_consumption_kw"].fillna(0)
    return agg


def merge_metadata(agg_df: pd.DataFrame, meta_df: pd.DataFrame) -> pd.DataFrame:
    """
    Join household metadata (square footage, age, solar presence, building type).
    """
    m = meta_df.copy()
    m["dataid"] = m["dataid"].astype(int)

    # Total square footage
    m["total_sqft"] = pd.to_numeric(m.get("total_square_footage"), errors="coerce").fillna(0)

    # House age (reference year: 2019)
    const_year = pd.to_numeric(m.get("construction_year"), errors="coerce")
    m["house_age"] = (2019 - const_year).clip(lower=0).fillna(0).astype(int)

    # Solar flags and size
    m["has_solar"] = (m.get("grid", "").astype(str).str.upper() == "YES").astype(int)
    m["pv_size_kw"] = pd.to_numeric(m.get("pv_size"), errors="coerce").fillna(0.0)

    # Building type encoding: 0 = Single-Family, 1 = Townhome, 2 = Apt/Other
    def _encode_bldg(val):
        val = str(val).lower()
        if "single" in val:
            return 0
        if "town" in val:
            return 1
        return 2

    m["building_type_code"] = m.get("building_type", "").map(_encode_bldg)

    meta_cols = ["dataid", "total_sqft", "house_age", "has_solar", "pv_size_kw", "building_type_code"]
    merged = pd.merge(agg_df, m[meta_cols], on="dataid", how="left")
    merged["total_sqft"] = merged["total_sqft"].fillna(0)
    merged["house_age"] = merged["house_age"].fillna(0)
    merged["has_solar"] = merged["has_solar"].fillna(0)
    merged["pv_size_kw"] = merged["pv_size_kw"].fillna(0.0)
    merged["building_type_code"] = merged["building_type_code"].fillna(0)
    return merged
