"""
Class 7 — Model workflow.

Joins the validated trip facts against the Zone dimension (pickup + dropoff)
and the WeatherHour dimension (by pickup hour), and engineers the fields the
metrics stage needs (hour-of-day, weekday, distance band).

Output: data/processed/trip_model_<month>.parquet — the modeled fact table
that metrics.py reads. This is the "relational/event model" deliverable for
Class 7 (see docs/data_model.md for the diagram this implements).
"""
import argparse
import json
import sys
from pathlib import Path

import pandas as pd

from utils.logging_utils import get_logger, StageError

RAW_DIR = Path("data/raw")
PROCESSED_DIR = Path("data/processed")

DISTANCE_BINS = [0, 2, 5, 10, float("inf")]
DISTANCE_LABELS = ["0-2mi", "2-5mi", "5-10mi", "10mi+"]


def load_zone_dim(logger) -> pd.DataFrame:
    path = RAW_DIR / "taxi_zone_lookup.csv"
    if not path.exists():
        raise StageError(f"Zone lookup not found: {path}. Run ingest first.")
    zones = pd.read_csv(path)
    logger.info(f"Loaded zone dimension: {len(zones):,} zones")
    return zones


def load_weather_dim(month: str, logger) -> pd.DataFrame:
    path = RAW_DIR / f"weather_{month}.json"
    if not path.exists():
        raise StageError(f"Weather file not found: {path}. Run ingest first.")
    with open(path) as f:
        payload = json.load(f)

    hourly = payload.get("hourly", {})
    if not hourly.get("time"):
        raise StageError("Weather payload has no hourly time series")

    weather = pd.DataFrame({
        "date_hour": pd.to_datetime(hourly["time"]),
        "temperature_c": hourly.get("temperature_2m", []),
        "precipitation_mm": hourly.get("precipitation", []),
    })
    logger.info(f"Loaded weather dimension: {len(weather):,} hourly records")
    return weather


def run(month: str) -> Path:
    logger = get_logger("transform", month)
    logger.info(f"=== TRANSFORM start: month={month} ===")

    valid_path = PROCESSED_DIR / f"trips_valid_{month}.parquet"
    if not valid_path.exists():
        raise StageError(f"Validated trips not found: {valid_path}. Run validate first.")

    trips = pd.read_parquet(valid_path)
    zones = load_zone_dim(logger)
    weather = load_weather_dim(month, logger)

    # Join pickup zone
    trips = trips.merge(
        zones.rename(columns={"LocationID": "PULocationID", "Zone": "pickup_zone",
                               "Borough": "pickup_borough"}),
        on="PULocationID", how="left",
    )
    # Join dropoff zone
    trips = trips.merge(
        zones.rename(columns={"LocationID": "DOLocationID", "Zone": "dropoff_zone",
                               "Borough": "dropoff_borough"}),
        on="DOLocationID", how="left", suffixes=("", "_do"),
    )

    unmatched_pu = trips["pickup_zone"].isna().sum()
    unmatched_do = trips["dropoff_zone"].isna().sum()
    if unmatched_pu or unmatched_do:
        logger.info(
            f"Zone join: {unmatched_pu:,} trips with unmatched pickup zone, "
            f"{unmatched_do:,} with unmatched dropoff zone "
            f"(should be ~0 since unmapped IDs were quarantined in validate.py)"
        )

    # Feature engineering
    trips["pickup_hour_of_day"] = trips["tpep_pickup_datetime"].dt.hour
    trips["pickup_weekday"] = trips["tpep_pickup_datetime"].dt.day_name()
    trips["pickup_date_hour"] = trips["tpep_pickup_datetime"].dt.floor("h")
    trips["distance_band"] = pd.cut(
        trips["trip_distance"], bins=DISTANCE_BINS, labels=DISTANCE_LABELS
    )

    # Join weather by the floored pickup hour
    trips = trips.merge(weather, left_on="pickup_date_hour", right_on="date_hour", how="left")
    unmatched_weather = trips["temperature_c"].isna().sum()
    if unmatched_weather:
        logger.info(
            f"Weather join: {unmatched_weather:,} trips with no matching hourly "
            f"weather record (likely at month-boundary edges)"
        )

    out_path = PROCESSED_DIR / f"trip_model_{month}.parquet"
    trips.to_parquet(out_path, index=False)
    logger.info(f"Wrote modeled fact table: {len(trips):,} rows -> {out_path}")
    logger.info("=== TRANSFORM complete ===")
    return out_path


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--month", required=True)
    args = parser.parse_args()
    try:
        run(args.month)
    except StageError as e:
        print(f"TRANSFORM FAILED: {e}", file=sys.stderr)
        sys.exit(1)
