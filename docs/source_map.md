# Source Map (Class 4)

## Business questions → required information → source systems

| Business question | Information required | Source system | Grain | Owner |
|---|---|---|---|---|
| How long do trips actually take, by zone and hour? | Pickup/dropoff timestamps, pickup/dropoff location IDs | TLC Yellow Trip Records | 1 row = 1 trip | NYC TLC (vendor-submitted) |
| What zone does a `LocationID` correspond to? | Zone name, borough, service zone | Taxi Zone Lookup Table | 1 row = 1 `LocationID` | NYC TLC |
| Is variance explained by weather, or is it "unexplained" (the interesting signal)? | Hourly precipitation, temperature | Open-Meteo Historical Weather API | 1 row = 1 hour, 1 location (NYC centroid) | Open-Meteo (aggregates NOAA/reanalysis data) |
| Is a trip financially efficient given its duration? | Fare amount, total amount | TLC Yellow Trip Records (same file) | 1 row = 1 trip | NYC TLC |

## Why these sources

- **TLC trip records** are the authoritative, publicly published record of
  the workflow itself (the trip). No other source can substitute.
- **Zone lookup table** is a small static dimension; without it, `LocationID`
  is a meaningless integer. Retrieved separately because it is versioned and
  updated independently of the trip data (different release cadence).
- **Weather API** is not authoritative over the trip data — it is
  contextual. It's included specifically to demonstrate a second retrieval
  mode (API vs. file) and to let the analysis distinguish "duration variance
  explained by weather" from "duration variance that is operationally
  interesting" (the latter is what should trigger an intervention).

## Ownership and known gaps

- TLC does not publish a trip ID, driver ID, or vehicle ID in the public
  dataset — trips cannot be traced to an individual driver or vehicle. This
  rules out any driver-level intervention metric.
- Pickup/dropoff timestamps and distance are **vendor self-reported**
  (from taxi meters), not independently measured by TLC. They are trusted
  but validated, not verified against an external ground truth.
- The zone lookup table is a coarse geography (263 zones) — it cannot
  support street-level or GPS-precision analysis; all "location" metrics in
  this project are necessarily zone-level, not point-level.
- Weather is measured at a single NYC-area point/grid cell, not per-zone —
  it is a citywide contextual signal, not a zone-specific one. This is a
  deliberate scope limitation, documented rather than silently assumed away.
- There is no real-time or "en-route" status in this dataset (no dispatch,
  no ETA, no driver acceptance event) — the workflow model in
  `data_model.md` reflects only the events that are actually observable in
  the source data (requested → picked up → dropped off → paid), not a
  richer workflow that isn't there.
