"""
Class 5 — Retrieval.

Two retrieval modes, as required:
  1. Bulk HTTP file download  -> TLC trip parquet + zone lookup CSV
  2. REST API pull (JSON)     -> Open-Meteo historical weather, paginated by
                                 the month's date range

Raw inputs are preserved untouched in data/raw/ — this module never mutates
what it downloads; validate.py is the only place transformation begins.
"""
import argparse
import hashlib
import json
import sys
from datetime import date
from pathlib import Path

import requests

from utils.logging_utils import get_logger, StageError

TLC_BASE_URL = "https://d37ci6vzurychx.cloudfront.net/trip-data"
ZONE_LOOKUP_URL = (
    "https://d37ci6vzurychx.cloudfront.net/misc/taxi_zone_lookup.csv"
)
# NYC centroid, used for a single citywide hourly weather series (see
# docs/known_unknown_assumptions.md for why this is citywide, not per-zone)
NYC_LAT, NYC_LON = 40.7128, -74.0060
WEATHER_API_URL = "https://archive-api.open-meteo.com/v1/archive"

RAW_DIR = Path("data/raw")


def _sha256_of_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def _download_file(url: str, dest: Path, logger, force: bool = False) -> Path:
    """Idempotent file download: skip if dest already exists and not forced."""
    if dest.exists() and not force:
        logger.info(
            f"SKIP download (already present): {dest.name} "
            f"({dest.stat().st_size:,} bytes, sha256={_sha256_of_file(dest)[:12]}...)"
        )
        return dest

    logger.info(f"Downloading {url} -> {dest}")
    try:
        with requests.get(url, stream=True, timeout=60) as r:
            r.raise_for_status()
            dest.parent.mkdir(parents=True, exist_ok=True)
            with open(dest, "wb") as f:
                for chunk in r.iter_content(chunk_size=1 << 20):
                    f.write(chunk)
    except requests.RequestException as e:
        raise StageError(f"Failed to download {url}: {e}") from e

    size = dest.stat().st_size
    if size == 0:
        raise StageError(f"Downloaded file {dest} is empty (0 bytes)")

    logger.info(
        f"OK: {dest.name} ({size:,} bytes, sha256={_sha256_of_file(dest)[:12]}...)"
    )
    return dest


def _month_date_range(month: str):
    year, mon = (int(x) for x in month.split("-"))
    start = date(year, mon, 1)
    end = date(year + 1, 1, 1) if mon == 12 else date(year, mon + 1, 1)
    return start.isoformat(), end.isoformat()


def _fetch_weather(month: str, dest: Path, logger, force: bool = False) -> Path:
    """API retrieval mode: Open-Meteo historical weather, hourly, for the month."""
    if dest.exists() and not force:
        logger.info(f"SKIP API pull (already present): {dest.name}")
        return dest

    start, end = _month_date_range(month)
    params = {
        "latitude": NYC_LAT,
        "longitude": NYC_LON,
        "start_date": start,
        "end_date": end,
        "hourly": "temperature_2m,precipitation",
        "timezone": "America/New_York",
    }
    logger.info(f"Calling weather API for {start}..{end}")
    try:
        resp = requests.get(WEATHER_API_URL, params=params, timeout=60)
        resp.raise_for_status()
        payload = resp.json()
    except requests.RequestException as e:
        raise StageError(f"Weather API call failed: {e}") from e

    if "hourly" not in payload or "time" not in payload.get("hourly", {}):
        raise StageError("Weather API response missing expected 'hourly.time' field")

    n_hours = len(payload["hourly"]["time"])
    logger.info(f"Weather API returned {n_hours} hourly records")

    dest.parent.mkdir(parents=True, exist_ok=True)
    with open(dest, "w") as f:
        json.dump(payload, f)

    return dest


def run(month: str, force: bool = False) -> dict:
    logger = get_logger("ingest", month)
    logger.info(f"=== INGEST start: month={month} force={force} ===")

    trip_url = f"{TLC_BASE_URL}/yellow_tripdata_{month}.parquet"
    trip_path = RAW_DIR / f"yellow_tripdata_{month}.parquet"
    zone_path = RAW_DIR / "taxi_zone_lookup.csv"
    weather_path = RAW_DIR / f"weather_{month}.json"

    outputs = {}
    outputs["trips"] = _download_file(trip_url, trip_path, logger, force)
    outputs["zones"] = _download_file(ZONE_LOOKUP_URL, zone_path, logger, force)
    outputs["weather"] = _fetch_weather(month, weather_path, logger, force)

    # Completeness check: TLC publishes monthly summary counts in its data
    # dictionary/dashboard. We can't hit an API for that (it's a PDF/webpage),
    # so we log what we retrieved and flag this as a manual cross-check
    # rather than pretending it's automated (see known_unknown_assumptions.md).
    logger.info(
        "Completeness note: row-count-vs-published-total is a MANUAL cross-"
        "check against TLC's monthly trip record summary; not automated here."
    )
    logger.info("=== INGEST complete ===")
    return outputs


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--month", required=True, help="YYYY-MM, e.g. 2024-01")
    parser.add_argument("--force-download", action="store_true")
    args = parser.parse_args()
    try:
        run(args.month, force=args.force_download)
    except StageError as e:
        print(f"INGEST FAILED: {e}", file=sys.stderr)
        sys.exit(1)
