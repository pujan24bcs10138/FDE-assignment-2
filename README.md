# NYC Taxi Operational Metrics Pipeline

A small, explainable, dependable pipeline that turns raw NYC TLC trip data into
trustworthy operational metrics: **trip duration predictability and efficiency
by pickup zone and hour.**

## 1. Problem

Ground-transportation operators (or a TLC analytics team) need to know **where
and when trip durations become unpredictable**, so that dispatch, routing, or
pricing interventions can be targeted rather than applied blanket-wide. Today
that answer is scattered across raw monthly trip files, a static zone lookup
table, and no consistent, automated way to combine them with external context
(e.g. weather) or to trust the output without re-deriving it from scratch
every time.

## 2. Users / stakeholders

- **Operations / dispatch leads** — want to know which zones/hours have
  unreliable trip durations worth investigating.
- **Data/analytics team** — needs a repeatable pipeline, not a one-off
  notebook, so the metric can be recomputed monthly without re-litigating
  data quality decisions each time.
- **FDE (this project)** — responsible for the trustworthy path from raw
  source systems to the metric.

## 3. Project KPI

**Trip Duration Predictability & Operational Efficiency by Pickup Zone / Hour**
— i.e., for a given zone and hour-of-day, how consistent are trip durations
for similar-distance trips, and how efficient is the resulting revenue per
trip-hour? Large, unexplained variance is the signal that something
operational (traffic, routing, demand mismatch) is worth investigating.

See [`docs/metrics.md`](docs/metrics.md) for the full metric definitions.

## 4. Source overview

| Source | Type | Retrieval mode | Grain | Owner |
|---|---|---|---|---|
| TLC Yellow Taxi Trip Records (monthly) | Parquet file | Bulk HTTP file download | 1 row = 1 trip | NYC TLC |
| Taxi Zone Lookup Table | CSV file | Bulk HTTP file download | 1 row = 1 `LocationID` | NYC TLC |
| Open-Meteo Historical Weather API | JSON | REST API (paginated by date) | 1 row = 1 hour, 1 location | Open-Meteo |

Full source reasoning, ownership, and known gaps are in
[`docs/source_map.md`](docs/source_map.md). Data model / workflow diagram is
in [`docs/data_model.md`](docs/data_model.md).

## 5. What the output supports

The final evidence table (`data/processed/metrics/`) supports a **go/no-go
decision on where to prioritize an operational review** — e.g., "investigate
dispatch in zone X during evening hours" — rather than a vague "traffic is
bad somewhere" statement. It is not a real-time monitoring tool; it is a
monthly, batch-computed reliability snapshot.

## 6. Repository layout

```
README.md
docs/
  source_map.md        # Class 4 — source reasoning, ownership, grain, gaps
  data_model.md         # Class 7 — entity/event model, mermaid diagram
  metrics.md            # Class 7 — metric definitions
  known_unknown_assumptions.md
src/
  ingest.py             # Class 5 — retrieval (file + API), raw preservation
  validate.py           # Class 6 — profiling + validation rules
  transform.py          # Class 7 — modeling, joins, feature engineering
  metrics.py            # Class 7 — metric computation
  run_pipeline.py        # Class 8 — orchestration, logging, rerun/failure handling
  utils/logging_utils.py
data/
  raw/                  # untouched source files (gitignored, downloaded on run)
  quarantine/           # rows that failed validation, with reason codes
  processed/            # validated + modeled data, and final metrics
logs/                   # per-run pipeline logs (gitignored)
notebooks/
  exploration.ipynb     # profiling / exploration, not the pipeline itself
```

## 7. Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## 8. Run instructions

```bash
# Full pipeline for a given month (downloads if not already present)
python src/run_pipeline.py --month 2024-01

# Re-run using already-downloaded raw data (idempotent — skips re-download)
python src/run_pipeline.py --month 2024-01

# Force re-download even if raw files already exist
python src/run_pipeline.py --month 2024-01 --force-download
```

Each stage logs row counts in/out/rejected to `logs/pipeline_<month>.log`.
A failed stage exits non-zero and leaves upstream outputs untouched — it does
not silently continue with partial data.

## 9. Known / Unknown / Assumption / Limitation

See [`docs/known_unknown_assumptions.md`](docs/known_unknown_assumptions.md)
for the full list. Summary: TLC trip records have no true trip ID, no
driver/vehicle identity, and self-reported timestamps/distances that are
validated but not independently verifiable — the pipeline flags implausible
values rather than silently discarding or "fixing" them.
