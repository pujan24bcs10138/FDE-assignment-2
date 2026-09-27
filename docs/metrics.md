# Metric Definitions (Class 7)

All metrics are computed per **pickup zone × pickup hour-of-day**, over the
selected month, from `is_valid == True` trips only (anomalous/rejected trips
are excluded from metrics 1/3/4/5 but ARE the numerator of metric 2 —
they are never silently dropped from the pipeline's accounting).

1. **Median trip duration (minutes)** — `median(duration_min)` per
   zone × hour. The baseline reliability measure.

2. **Anomaly rate (%)** — `count(is_anomalous) / count(all trips)` per
   zone × hour. A data-quality / operational-reliability signal: a rising
   anomaly rate in a zone/hour can mean bad GPS/meter data OR genuinely
   erratic trips (e.g. traffic incidents) — either way, worth flagging.

3. **Revenue per trip-hour ($)** — `sum(total_amount) / sum(duration_min/60)`
   per zone × hour. Operational efficiency: are longer trips in a zone
   actually paying for the time they take?

4. **Trip volume & average distance** — `count(trips)`,
   `mean(trip_distance)` per zone × hour. Demand-pattern context needed to
   interpret the other metrics (a "high variance" zone with 3 trips/month
   is not the same signal as one with 3,000).

5. **Duration predictability (core KPI)** — for trips grouped into
   distance bands (e.g. 0–2mi, 2–5mi, 5–10mi, 10mi+) within each
   zone × hour, the **coefficient of variation** (`stddev / mean`) of
   `duration_min`. High CoV = low predictability = the primary signal for
   where an operational intervention should be investigated.

## Why these five

They map directly to the project KPI (predictability + efficiency) while
keeping the output small enough to fit in a single evidence table, per the
assignment's "we are not grading project size" guidance. Metric 5 is the
one the demo should center on — it's the metric that best distinguishes
"just busy" zones from "actually unpredictable" zones.
