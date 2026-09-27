# Workflow / Data Model (Class 7)

## Entities

- **Trip** (fact / event record): the core unit of work. One row per
  observed trip in the source data.
- **Zone** (dimension): `LocationID → Borough, Zone name, service_zone`.
  Used for both pickup and dropoff.
- **WeatherHour** (dimension/context): `date_hour, temperature_c,
  precipitation_mm` for NYC, joined to trips by the pickup hour.

## Events / states represented per trip

A trip in this dataset is observed at exactly these state transitions —
no more, no less (see `source_map.md` for why richer workflow states like
"dispatch requested" or "driver assigned" are NOT modeled: they don't exist
in the source):

```
requested/hailed → picked_up (pickup_datetime, PULocationID)
                  → dropped_off (dropoff_datetime, DOLocationID)
                  → paid (fare_amount, total_amount, payment_type)
```

## Interventions / outcomes (as derived, not source, fields)

- `is_valid` — did the trip pass all validation rules (Class 6)?
- `duration_min`, `implied_speed_mph` — derived operational fields.
- `is_anomalous` — flagged by validation (impossible speed/duration), kept
  and labeled rather than dropped, because the anomaly rate is itself a
  reliability metric.
- `revenue_per_trip_hour` — outcome/efficiency field.

## Relational model (simplified star schema)

```mermaid
erDiagram
    TRIP_FACT }o--|| ZONE_DIM : "PULocationID → LocationID"
    TRIP_FACT }o--|| ZONE_DIM : "DOLocationID → LocationID"
    TRIP_FACT }o--o| WEATHER_HOUR : "pickup_hour → date_hour"

    TRIP_FACT {
        datetime pickup_datetime
        datetime dropoff_datetime
        int PULocationID
        int DOLocationID
        float trip_distance
        float fare_amount
        float total_amount
        float duration_min
        float implied_speed_mph
        bool is_valid
        bool is_anomalous
        string reject_reason
    }
    ZONE_DIM {
        int LocationID
        string Borough
        string Zone
        string service_zone
    }
    WEATHER_HOUR {
        datetime date_hour
        float temperature_c
        float precipitation_mm
    }
```

## Workflow diagram (event flow)

```mermaid
flowchart LR
    A[Trip requested/hailed] --> B[Picked up<br/>pickup_datetime, PULocationID]
    B --> C[Dropped off<br/>dropoff_datetime, DOLocationID]
    C --> D[Paid<br/>fare_amount, total_amount]
    D --> E{Validation}
    E -->|pass| F[Trip fact table]
    E -->|fail| G[Quarantine + reason code]
    F --> H[Join Zone dim + Weather dim]
    H --> I[Metrics: duration predictability,<br/>anomaly rate, revenue/trip-hour,<br/>volume, variance]
```
