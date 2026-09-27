# 2-Minute Video Submission Script & Screen Guide

> **Assignment Track**: Track B — NYC TLC Taxi Operational Pipeline  
> **Target Duration**: ~2 minutes (120 seconds, ~270 words)  
> **Tone**: Confident, concise, professional, and engineering-focused ("Think like an FDE").

---

## Quick Recording Checklist Before You Hit Record
1. **Screen Layout**:
   - Have VS Code or your GitHub repository open on the left.
   - Have a clean terminal open on the right (or bottom panel).
2. **Tabs to Have Pre-Opened in VS Code / Browser**:
   - Tab 1: `README.md` (Sections 1–3: Problem & KPI)
   - Tab 2: `docs/data_model.md` (The Mermaid Workflow diagram)
   - Tab 3: `src/validate.py` (Validation rules & quarantine logic)
   - Tab 4: `docs/metrics.md` / `src/run_pipeline.py` (Pipeline architecture & metrics)
3. **Pacing**: Speak at a steady, conversational pace (~130 words per minute). Don't rush!

---

## Timed Video Script & Visual Walkthrough

---

### Segment 1: Problem Statement & Stakeholder KPI (0:00 – 0:30)

#### 🖥️ What to Show on Screen:
- Start on **`README.md`**, highlighting **Section 1 (Problem)**, **Section 2 (Stakeholders)**, and **Section 3 (Project KPI)**.
- Switch briefly to **`docs/data_model.md`** to show the workflow flowchart (`requested` $\rightarrow$ `picked_up` $\rightarrow$ `dropped_off` $\rightarrow$ `paid`).

#### 🎙️ What to Say (Spoken Script):
> "Hi, I'm presenting the NYC TLC Operational Pipeline for Track B.
> 
> In transportation operations, dispatch leads struggle with a core problem: they know delays happen, but they can't pinpoint **where and when** trip durations become unpredictable versus when they are just predictably busy.
> 
> Our project KPI is **Trip Duration Predictability and Revenue Efficiency by Pickup Zone and Hour**. Rather than building a generic data analysis, this project creates a repeatable path from raw operational systems to targeted dispatch decisions."

---

### Segment 2: Multi-Source Retrieval & Architecture (0:30 – 0:55)

#### 🖥️ What to Show on Screen:
- Switch to **`docs/source_map.md`** (the source mapping table) or **`src/ingest.py`**.
- Briefly show the `data/raw/` directory structure.

#### 🎙️ What to Say (Spoken Script):
> "To answer this, our pipeline integrates multiple sources across two distinct retrieval modes:
> 
> First, bulk HTTP file retrieval for monthly TLC Yellow Trip Parquet records and the static Taxi Zone lookup CSV.
> Second, a REST API integration pulling hourly weather data from Open-Meteo as external context.
> 
> Raw inputs are preserved completely untouched in `data/raw/`, ensuring full reproducibility and auditability."

---

### Segment 3: The Core FDE Judgement Call (0:55 – 1:35) ⭐ *Key Rubric Requirement*

#### 🖥️ What to Show on Screen:
- Open **`src/validate.py`** and scroll to lines showing the hard validation checks and the quarantine output (`trips_rejected` with `reason_code`).
- Point to **`docs/known_unknown_assumptions.md`** or **`docs/metrics.md`** showing the Coefficient of Variation metric.

#### 🎙️ What to Say (Spoken Script):
> "The central FDE judgement call I made was: **never silently drop or impute messy client data — instead, quarantine it and turn data quality into an observable metric**.
> 
> Taxi meter data is notoriously dirty — with clock resets, negative fares, and extreme speeds. Rather than silently fixing or dropping them, our validation stage separates trips into valid data and a dedicated quarantine table, tagging every rejected row with an explicit reason code.
> 
> Furthermore, instead of using raw average trip duration — which misleadingly penalizes naturally longer trips — I defined predictability using the **Coefficient of Variation within distance bands**. This isolates genuine operational variance from distance."

---

### Segment 4: Pipeline Dependability & Decision Output (1:35 – 2:00)

#### 🖥️ What to Show on Screen:
- Switch to terminal and highlight the execution of `src/run_pipeline.py`.
- Show a sample log line from `logs/pipeline_2024-01.log` or the resulting evidence table structure.

#### 🎙️ What to Say (Spoken Script):
> "Finally, pipeline dependability is built-in: the workflow runs end-to-end as **Ingest $\rightarrow$ Validate $\rightarrow$ Transform $\rightarrow$ Metrics**.
> 
> It is strictly idempotent — re-running never duplicates data or re-downloads unnecessarily. If any stage encounters an error, it halts immediately without corrupting upstream outputs.
> 
> The final output is an evidence table ranking the least predictable zones and hours, giving dispatch leads the exact evidence needed to deploy targeted operational interventions."

---

## Summary of Rubric Alignment Covered in the 2 Minutes

| Time | Rubric Criterion Covered | Key Phrase to Hit |
|---|---|---|
| **0:00–0:30** | Source Reasoning & KPI (20%) | *"Trip duration predictability and revenue efficiency by zone and hour"* |
| **0:30–0:55** | Retrieval (20%) | *"Two retrieval modes: bulk HTTP download + REST API, raw inputs preserved"* |
| **0:55–1:35** | Validation & FDE Judgement (20%) | *"Quarantine with explicit reason codes instead of silent dropping"* |
| **1:35–2:00** | Workflow, Metrics & Dependability (40%) | *"Idempotent pipeline, halts on failure, actionable evidence table"* |
