"""
prepare_pecan_dataset.py
========================
Aggregates the Pecan Street 15-minute interval data (preprocessed_data.csv)
into monthly per-home features and joins household metadata (metadata.csv).

Output: pecan_train_ready.csv  (one row per home-month)

Features produced (NO DATA LEAKAGE)
------------------------------------
Temporal
    month                   int  1-12
    year                    int
    season                  int  0=Spring 1=Summer 2=Fall 3=Winter

Home metadata (from metadata.csv)
    total_sqft              float  total square footage (0 if unknown)
    house_age               int    2019 - construction_year (0 if unknown)
    has_solar               int    1 if PV system present else 0
    pv_size_kw              float  total PV capacity in kW (0 if none)
    building_type_code      int    0=Single-Family  1=TownHome  2=Apartment/Other
    num_monitored_circuits  int    count of non-null circuit columns in the raw data

Usage pattern features (lag/history - available BEFORE prediction)
    peak_15min_kw           float  maximum 15-min grid reading in the month
    std_consumption_kw      float  std-dev of 15-min grid readings (variability)
    daytime_ratio           float  fraction of consumption in 06:00-22:00 window

TARGET
    house_consumption_kwh   float  TOTAL monthly kWh consumed (TARGET)

REMOVED LEAKY FEATURES (to prevent data leakage):
    grid_consumption_kwh    IS the target (house_consumption = grid draw)
    avg_daily_kwh           derived from target (consumption / days)
    energy_sold_kwh         contains target (solar - consumption)
    solar_offset_ratio      contains target (solar / consumption)
    solar_generation_kwh    same-month generation (not available beforehand)
    night_ratio             redundant with daytime_ratio (night = 1 - daytime)

Usage:
    python prepare_pecan_dataset.py
"""

import os
import pandas as pd
import numpy as np

# -- CONFIG -------------------------------------------------------------------

ENERGY_CSV   = "preprocessed_data.csv"
METADATA_CSV = os.path.join("Dataset", "metadata.csv")
OUTPUT_CSV   = "pecan_train_ready.csv"

# All circuit-level power columns (used for circuit count + daytime ratio)
CIRCUIT_COLS = [
    "air1","air2","air3","airwindowunit1","aquarium1","bathroom1","bathroom2",
    "bedroom1","bedroom2","bedroom3","bedroom4","bedroom5","battery1","car1",
    "car2","circpump1","clotheswasher1","clotheswasher_dryg1","diningroom1",
    "diningroom2","dishwasher1","disposal1","drye1","dryg1","freezer1",
    "furnace1","furnace2","garage1","garage2","heater1","heater2","heater3",
    "housefan1","icemaker1","jacuzzi1","kitchen1","kitchen2","kitchenapp1",
    "kitchenapp2","lights_plugs1","lights_plugs2","lights_plugs3","lights_plugs4",
    "lights_plugs5","lights_plugs6","livingroom1","livingroom2","microwave1",
    "office1","outsidelights_plugs1","outsidelights_plugs2","oven1","oven2",
    "pool1","pool2","poollight1","poolpump1","pump1","range1","refrigerator1",
    "refrigerator2","security1","sewerpump1","shed1","sprinkler1","sumppump1",
    "utilityroom1","venthood1","waterheater1","waterheater2","wellpump1","winecooler1",
]

# -- LOAD ENERGY DATA ---------------------------------------------------------

print(f"Loading energy data from: {ENERGY_CSV}")
df = pd.read_csv(ENERGY_CSV, parse_dates=["local_15min"])
print(f"  Rows: {len(df):,}  |  Homes: {df['dataid'].nunique()}  |  "
      f"Range: {df['local_15min'].min().date()} -> {df['local_15min'].max().date()}")

# -- PARSE TIME FEATURES ------------------------------------------------------

df["year"]  = df["local_15min"].dt.year
df["month"] = df["local_15min"].dt.month
df["hour"]  = df["local_15min"].dt.hour

# daytime window: 06:00 - 21:59
df["is_daytime"] = ((df["hour"] >= 6) & (df["hour"] < 22)).astype(int)

# season: 0=Spring(3-5) 1=Summer(6-8) 2=Fall(9-11) 3=Winter(12,1,2)
def to_season(m):
    if m in (3, 4, 5):   return 0
    if m in (6, 7, 8):   return 1
    if m in (9, 10, 11): return 2
    return 3

df["season"] = df["month"].map(to_season)

# -- CIRCUIT COUNT PER ROW ----------------------------------------------------
# Count how many circuit columns have a non-null reading per row.
# We later take the max across the month so we know how many circuits the home has.

present_circuits = [c for c in CIRCUIT_COLS if c in df.columns]
df["n_circuits_row"] = df[present_circuits].notna().sum(axis=1)

# -- DAYTIME CONSUMPTION ------------------------------------------------------
# grid kWh per 15-min interval = grid_kW * (15/60)
# solar generation = solar column (also in kW)

df["grid_kw"]  = df["grid"].fillna(0).clip(lower=0)
df["solar_kw"] = df["solar"].fillna(0).clip(lower=0)

# 15-min energy in kWh
df["grid_kwh_interval"]  = df["grid_kw"]  * (15 / 60)
df["solar_kwh_interval"] = df["solar_kw"] * (15 / 60)

# daytime grid
df["grid_kwh_daytime"] = df["grid_kwh_interval"] * df["is_daytime"]

# -- AGGREGATE TO MONTHLY PER HOME --------------------------------------------

print("Aggregating to monthly per-home records...")

grp = df.groupby(["dataid", "year", "month"])

agg = grp.agg(
    # Total consumption (grid draw is our proxy for house consumption)
    grid_consumption_kwh  = ("grid_kwh_interval",  "sum"),
    solar_generation_kwh  = ("solar_kwh_interval", "sum"),
    grid_kwh_daytime      = ("grid_kwh_daytime",   "sum"),

    # Peak and variability of the raw 15-min grid readings (in kW)
    peak_15min_kw         = ("grid_kw",  "max"),
    std_consumption_kw    = ("grid_kw",  "std"),

    # Season (same for all rows in a month)
    season                = ("season",   "first"),

    # Circuit count (max across rows)
    num_monitored_circuits = ("n_circuits_row", "max"),

    # Row count to derive days
    n_intervals            = ("grid_kw",  "count"),
).reset_index()

# -- DERIVED FEATURES ---------------------------------------------------------

# House consumption = grid draw (no battery storage modelling needed here)
agg["house_consumption_kwh"] = agg["grid_consumption_kwh"]

# Energy sold = solar surplus over house consumption (clip at 0)
agg["energy_sold_kwh"] = (
    agg["solar_generation_kwh"] - agg["house_consumption_kwh"]
).clip(lower=0)

# Solar offset ratio (0 where no solar)
agg["solar_offset_ratio"] = np.where(
    agg["house_consumption_kwh"] > 0,
    (agg["solar_generation_kwh"] / agg["house_consumption_kwh"]).clip(0, 1),
    0.0,
)

# Average daily kWh  (n_intervals * 15min = total minutes; /60/24 = days)
agg["days_in_month"] = (agg["n_intervals"] * 15 / 60 / 24).round(1)
agg["avg_daily_kwh"] = np.where(
    agg["days_in_month"] > 0,
    agg["house_consumption_kwh"] / agg["days_in_month"],
    0.0,
)

# Daytime ratio (fraction of consumption during 06:00-22:00)
agg["daytime_ratio"] = np.where(
    agg["grid_consumption_kwh"] > 0,
    agg["grid_kwh_daytime"] / agg["grid_consumption_kwh"],
    0.5,
).clip(0, 1)
agg["night_ratio"] = 1.0 - agg["daytime_ratio"]

# std_consumption_kw: fill NaN (single-row months) with 0
agg["std_consumption_kw"] = agg["std_consumption_kw"].fillna(0)

# -- JOIN METADATA -------------------------------------------------------------

print(f"Loading metadata from: {METADATA_CSV}")

# Row 0 = short column names (dataid, building_type, ...)
# Row 1 = long descriptions  -> skip it
# Row 2+ = actual data
meta_raw = pd.read_csv(METADATA_CSV, header=0, skiprows=[1], low_memory=False)
print(f"  Metadata rows: {len(meta_raw)}")
print(f"  Metadata columns (first 10): {meta_raw.columns.tolist()[:10]}")
meta_raw["dataid"] = pd.to_numeric(meta_raw["dataid"], errors="coerce")
meta_raw = meta_raw.dropna(subset=["dataid"])
meta_raw["dataid"] = meta_raw["dataid"].astype(int)
print(f"  Valid dataid rows: {len(meta_raw)}")

# Select relevant metadata columns
# Columns: building_type, house_construction_year, total_square_footage, pv, total_amount_of_pv
meta = meta_raw[["dataid", "building_type", "house_construction_year",
                  "total_square_footage", "pv", "total_amount_of_pv"]].copy()

# building_type_code
def encode_building(val):
    if pd.isna(val):
        return 0
    v = str(val).strip().lower()
    if "single" in v:  return 0
    if "town"   in v:  return 1
    return 2   # apartment or other

meta["building_type_code"] = meta["building_type"].apply(encode_building)

# has_solar
meta["has_solar"] = (meta["pv"].astype(str).str.strip().str.lower() == "yes").astype(int)

# pv_size_kw
meta["pv_size_kw"] = pd.to_numeric(meta["total_amount_of_pv"], errors="coerce").fillna(0.0)

# house_age (relative to 2019, last year in the dataset)
meta["construction_year"] = pd.to_numeric(meta["house_construction_year"], errors="coerce")
meta["house_age"] = (2019 - meta["construction_year"]).clip(lower=0).fillna(0).astype(int)

# total_sqft
meta["total_sqft"] = pd.to_numeric(meta["total_square_footage"], errors="coerce").fillna(0.0)

meta_clean = meta[["dataid", "building_type_code", "has_solar",
                    "pv_size_kw", "house_age", "total_sqft"]].copy()

# merge (left join keeps all energy rows even if metadata missing)
agg = agg.merge(meta_clean, on="dataid", how="left")

# fill any missing metadata with defaults
agg["building_type_code"] = agg["building_type_code"].fillna(0).astype(int)
agg["has_solar"]           = agg["has_solar"].fillna(0).astype(int)
agg["pv_size_kw"]          = agg["pv_size_kw"].fillna(0.0)
agg["house_age"]           = agg["house_age"].fillna(0).astype(int)
agg["total_sqft"]          = agg["total_sqft"].fillna(0.0)

# -- FINAL COLUMN SELECTION & ORDERING ----------------------------------------

FINAL_COLS = [
    # identifiers (not used as model features - kept for traceability)
    "dataid", "year", "month",

    # temporal
    "season",

    # home metadata features (static - available before prediction)
    "total_sqft",
    "house_age",
    "has_solar",
    "pv_size_kw",
    "building_type_code",
    "num_monitored_circuits",

    # usage pattern features (lag/history - available before prediction)
    "peak_15min_kw",
    "std_consumption_kw",
    "daytime_ratio",

    # TARGET
    "house_consumption_kwh",
]

# NOTE: Removed leaky features to prevent data leakage:
# - grid_consumption_kwh: IS the target (house_consumption = grid draw)
# - avg_daily_kwh: derived from target (consumption / days)
# - energy_sold_kwh: contains target (solar - consumption)
# - solar_offset_ratio: contains target (solar / consumption)
# - solar_generation_kwh: same-month generation (not available beforehand)
# - night_ratio: perfectly redundant with daytime_ratio (night = 1 - daytime)

output = agg[FINAL_COLS].copy()

# Drop rows with zero consumption (no data recorded that month)
before = len(output)
output = output[output["house_consumption_kwh"] > 0].reset_index(drop=True)
after  = len(output)
print(f"  Dropped {before - after} rows with zero consumption.")

# -- SAVE ---------------------------------------------------------------------

output.to_csv(OUTPUT_CSV, index=False)
print(f"\nSaved: {OUTPUT_CSV}  |  Shape: {output.shape}")

# -- SUMMARY ------------------------------------------------------------------

print("\n-- Dataset summary --------------------------------------------------")
print(output.describe().to_string())
print("\nSolar homes in dataset:",
      output[output["has_solar"] == 1]["dataid"].nunique(),
      "of", output["dataid"].nunique(), "total homes")
print("Monthly records per home:")
print(output.groupby("dataid")["month"].count().describe().to_string())
print("\nDone. Run train_with_noise_and_save.py next.")
