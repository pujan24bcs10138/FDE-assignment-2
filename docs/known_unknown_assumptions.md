# Known / Unknown / Assumption / Limitation

## Known
- Trip records are vendor-submitted via taxi meters; TLC publishes them
  as-is with no correction.
- The zone lookup table has 263 zones across 5 boroughs, including
  `Unknown` and `N/A` placeholder zones (IDs 264, 265).
- Weather is a single citywide series, not per-zone.

## Unknown
- Whether a given trip's timestamps reflect meter start/stop precisely or
  include dispatch/wait time — TLC's own documentation is ambiguous here,
  so `duration_min` is treated as "observed trip duration," not strictly
  "in-motion time."
- Driver/vehicle identity — genuinely absent from the source; any metric
  implying "which drivers" would be fabricated, so none is attempted.

## Assumptions
- Trips with `PULocationID` or `DOLocationID` of 264/265 ("Unknown"/"N/A")
  are kept in the raw data but excluded from zone-level metrics (they
  can't be assigned to a real zone) — logged as a distinct quarantine
  reason, not merged into "invalid."
- A trip is treated as belonging to the pickup hour of its
  `pickup_datetime` for weather-joining purposes, even though the trip may
  span into the next hour.
- Distance bands for the predictability metric (0–2/2–5/5–10/10+ miles)
  are a reasonable operational split, not a value derived from the data
  itself — documented as a judgment call.

## Limitations
- No ground truth exists to verify whether a flagged "anomalous" trip is a
  data error or a real (if unusual) trip — the pipeline flags, it does not
  adjudicate.
- The pipeline is monthly/batch; it cannot detect an emerging problem
  intra-month.
- Weather's citywide grain means it can rule out "the whole city was
  under a storm" but cannot explain zone-specific variance — this is the
  main reason metric 5 (predictability) is reported per zone rather than
  attributed to weather.
