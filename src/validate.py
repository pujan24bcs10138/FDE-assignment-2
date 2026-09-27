"""
Class 6 — Profile & validate.

Profiles the raw trip data, applies business-oriented validation rules, and
splits rows into:
  - data/processed/trips_valid_<month>.parquet   (is_valid == True)
  - data/quarantine/trips_rejected_<month>.parquet (is_valid == False, with reason_code)

Nothing is silently dropped or "fixed" — every rejected row keeps its
reason_code so the quarantine file itself is evidence, per the assignment's
"record assumptions/limitations instead of silently fixing them."
"""
import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from utils.logging_utils import get_logger, StageError

RAW_DIR = Path("data/raw")
PROCESSED_DIR = Path("data/processed")
QUARANTINE_DIR = Path("data/quarantine")

# Business-oriented thresholds — documented, not arbitrary magic numbers
MAX_TRIP_HOURS = 4
MAX_TRIP_DISTANCE_MI = 100
MAX_IMPLIED_SPEED_MPH = 80
UNKNOWN_ZONE_IDS = {264, 265}


def profile(df: pd.DataFrame, logger) -> None:
    """Log a lightweight data profile — counts, nulls, ranges — before validating."""
    logger.info(f"Profile: {len(df):,} raw rows, {df.shape[1]} columns")
    null_counts = df.isnull().sum()
    interesting_nulls = null_counts[null_counts > 0]
    if len(interesting_nulls):
        logger.info(f"Null counts (non-zero): {interesting_nulls.to_dict()}")
    if "trip_distance" in df.columns:
        logger.info(
            f"trip_distance: min={df.trip_distance.min():.2f} "
            f"max={df.trip_distance.max():.2f} "
            f"mean={df.trip_distance.mean():.2f}"
        )
    if "fare_amount" in df.columns:
        logger.info(
            f"fare_amount: min={df.fare_amount.min():.2f} "
            f"max={df.fare_amount.max():.2f} "
            f"negative_count={(df.fare_amount < 0).sum()}"
        )


def apply_validation_rules(df: pd.DataFrame, logger) -> pd.DataFrame:
    """Return df with is_valid, is_anomalous, reason_code columns added.

    A trip can be invalid (excluded from all metrics) or merely anomalous
    (kept, but flagged and counted in the anomaly-rate metric) — see
    docs/metrics.md for why these are treated differently.
    """
    df = df.copy()
    df["duration_min"] = (
        df["tpep_dropoff_datetime"] - df["tpep_pickup_datetime"]
    ).dt.total_seconds() / 60.0

    reasons = pd.Series([""] * len(df), index=df.index)

    def flag(mask, reason, current):
        """Vectorized reason-code append: adds `;reason` only where current
        already has content, else just `reason` — for rows where mask is True."""
        sep = np.where(current.str.len() > 0, ";", "")
        appended = current + sep + reason
        return current.where(~mask, appended)

    # Hard invalidation rules — excluded from all metrics
    bad_time_order = df["duration_min"] <= 0
    reasons = flag(bad_time_order, "dropoff_before_or_equal_pickup", reasons)

    too_long = df["duration_min"] > MAX_TRIP_HOURS * 60
    reasons = flag(too_long, f"duration_over_{MAX_TRIP_HOURS}h", reasons)

    bad_distance = (df["trip_distance"] <= 0) | (df["trip_distance"] > MAX_TRIP_DISTANCE_MI)
    reasons = flag(bad_distance, "distance_out_of_range", reasons)

    unknown_pu = df["PULocationID"].isin(UNKNOWN_ZONE_IDS)
    unknown_do = df["DOLocationID"].isin(UNKNOWN_ZONE_IDS)
    reasons = flag(unknown_pu | unknown_do, "unmapped_zone_id", reasons)

    negative_fare = df["fare_amount"] < 0
    reasons = flag(negative_fare, "negative_fare", reasons)

    is_invalid = bad_time_order | too_long | bad_distance | unknown_pu | unknown_do | negative_fare

    # Soft anomaly rule — kept, but flagged (only meaningful where duration > 0)
    safe_duration_hr = df["duration_min"].clip(lower=1e-6) / 60.0
    implied_speed = df["trip_distance"] / safe_duration_hr
    is_anomalous = (~is_invalid) & (implied_speed > MAX_IMPLIED_SPEED_MPH)
    reasons = flag(is_anomalous, "implausible_speed", reasons)

    df["implied_speed_mph"] = implied_speed
    df["is_valid"] = ~is_invalid
    df["is_anomalous"] = is_anomalous
    df["reason_code"] = reasons.replace("", np.nan)

    logger.info(
        f"Validation: {is_invalid.sum():,} invalid rows, "
        f"{is_anomalous.sum():,} anomalous (kept, flagged), "
        f"{(~is_invalid).sum():,} valid rows"
    )
    return df


def run(month: str) -> dict:
    logger = get_logger("validate", month)
    logger.info(f"=== VALIDATE start: month={month} ===")

    trip_path = RAW_DIR / f"yellow_tripdata_{month}.parquet"
    if not trip_path.exists():
        raise StageError(f"Raw trip file not found: {trip_path}. Run ingest first.")

    df = pd.read_parquet(trip_path)
    profile(df, logger)

    required_cols = {
        "tpep_pickup_datetime", "tpep_dropoff_datetime",
        "PULocationID", "DOLocationID", "trip_distance",
        "fare_amount", "total_amount",
    }
    missing = required_cols - set(df.columns)
    if missing:
        raise StageError(f"Raw trip file missing expected columns: {missing}")

    df = apply_validation_rules(df, logger)

    valid_df = df[df["is_valid"]].copy()
    rejected_df = df[~df["is_valid"]].copy()

    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    QUARANTINE_DIR.mkdir(parents=True, exist_ok=True)

    valid_out = PROCESSED_DIR / f"trips_valid_{month}.parquet"
    rejected_out = QUARANTINE_DIR / f"trips_rejected_{month}.parquet"
    valid_df.to_parquet(valid_out, index=False)
    rejected_df.to_parquet(rejected_out, index=False)

    if len(rejected_df):
        reason_summary = rejected_df["reason_code"].value_counts().to_dict()
        logger.info(f"Rejection reasons: {reason_summary}")

    logger.info(
        f"Wrote {len(valid_df):,} valid rows -> {valid_out}, "
        f"{len(rejected_df):,} rejected rows -> {rejected_out}"
    )
    logger.info("=== VALIDATE complete ===")
    return {"valid": valid_out, "rejected": rejected_out}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--month", required=True)
    args = parser.parse_args()
    try:
        run(args.month)
    except StageError as e:
        print(f"VALIDATE FAILED: {e}", file=sys.stderr)
        sys.exit(1)
