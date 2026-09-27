"""
Class 7 — Metrics (the final evidence table).

Reads the modeled fact table and computes the 5 metrics defined in
docs/metrics.md, writing one CSV per metric plus a combined markdown
evidence table under data/processed/metrics/.
"""
import argparse
import sys
from pathlib import Path

import pandas as pd

from utils.logging_utils import get_logger, StageError

PROCESSED_DIR = Path("data/processed")
METRICS_DIR = PROCESSED_DIR / "metrics"


def compute_metrics(df: pd.DataFrame, logger) -> dict:
    grp = df.groupby(["pickup_zone", "pickup_hour_of_day"], observed=True)

    # 1. Median trip duration
    median_duration = grp["duration_min"].median().rename("median_duration_min")

    # 2. Anomaly rate — computed over ALL trips (valid + rejected would need
    # the pre-quarantine set; here we report the anomaly rate among trips
    # that passed hard validation but were flagged soft-anomalous)
    anomaly_rate = grp["is_anomalous"].mean().rename("anomaly_rate")

    # 3. Revenue per trip-hour
    revenue = grp.apply(
        lambda g: g["total_amount"].sum() / (g["duration_min"].sum() / 60.0)
        if g["duration_min"].sum() > 0 else float("nan"),
        include_groups=False,
    ).rename("revenue_per_trip_hour")

    # 4. Volume & average distance
    volume = grp.size().rename("trip_count")
    avg_distance = grp["trip_distance"].mean().rename("avg_distance_mi")

    # 5. Duration predictability (CoV) within distance bands
    predictability = (
        df.groupby(["pickup_zone", "pickup_hour_of_day", "distance_band"], observed=True)
        ["duration_min"]
        .agg(["mean", "std"])
        .assign(coefficient_of_variation=lambda x: x["std"] / x["mean"])
        .reset_index()
    )

    evidence = pd.concat(
        [median_duration, anomaly_rate, revenue, volume, avg_distance], axis=1
    ).reset_index()

    logger.info(f"Computed metrics for {len(evidence):,} zone x hour groups")
    logger.info(
        f"Predictability table: {len(predictability):,} "
        f"zone x hour x distance_band groups"
    )

    return {"evidence": evidence, "predictability": predictability}


def write_markdown_summary(evidence: pd.DataFrame, predictability: pd.DataFrame, path: Path):
    top_unpredictable = (
        predictability.dropna(subset=["coefficient_of_variation"])
        .sort_values("coefficient_of_variation", ascending=False)
        .head(10)
    )
    lines = ["# Metrics Evidence Table\n"]
    lines.append("## Top 10 least-predictable zone/hour/distance-band combinations\n")
    lines.append(top_unpredictable.to_markdown(index=False))
    lines.append("\n\n## Zone x hour summary (first 20 rows, sorted by volume)\n")
    lines.append(
        evidence.sort_values("trip_count", ascending=False).head(20).to_markdown(index=False)
    )
    path.write_text("\n".join(lines))


def run(month: str) -> dict:
    logger = get_logger("metrics", month)
    logger.info(f"=== METRICS start: month={month} ===")

    model_path = PROCESSED_DIR / f"trip_model_{month}.parquet"
    if not model_path.exists():
        raise StageError(f"Modeled fact table not found: {model_path}. Run transform first.")

    df = pd.read_parquet(model_path)
    results = compute_metrics(df, logger)

    METRICS_DIR.mkdir(parents=True, exist_ok=True)
    evidence_path = METRICS_DIR / f"evidence_table_{month}.csv"
    predictability_path = METRICS_DIR / f"predictability_{month}.csv"
    summary_path = METRICS_DIR / f"summary_{month}.md"

    results["evidence"].to_csv(evidence_path, index=False)
    results["predictability"].to_csv(predictability_path, index=False)
    write_markdown_summary(results["evidence"], results["predictability"], summary_path)

    logger.info(f"Wrote {evidence_path}, {predictability_path}, {summary_path}")
    logger.info("=== METRICS complete ===")
    return {
        "evidence": evidence_path,
        "predictability": predictability_path,
        "summary": summary_path,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--month", required=True)
    args = parser.parse_args()
    try:
        run(args.month)
    except StageError as e:
        print(f"METRICS FAILED: {e}", file=sys.stderr)
        sys.exit(1)
