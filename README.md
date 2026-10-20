# SMARD Energy Pipeline

> Work in progress. Scope and decisions: [`SCOPE.md`](SCOPE.md).

A daily-updating data pipeline for the German electricity market. It pulls generation by source, consumption and day-ahead prices from [SMARD](https://www.smard.de) (Bundesnetzagentur), models them in DuckDB with dbt and feeds a dashboard that asks: **how much do wind and solar push down the electricity price, and when do they push it below zero?**

## Planned architecture

```
SMARD API ──► src/ingest (Python) ──► data/raw/*.parquet ──► dbt + DuckDB ──► marts ──► Streamlit dashboard
                     ▲                                          │
                     └──────── GitHub Actions, daily ───────────┘ tests
```

## Project structure

```
smard-energy-pipeline/
├── SCOPE.md          # what is in and out, and why
├── docs/api_notes.md # verified facts about the SMARD API
├── src/
│   ├── series.py     #   which SMARD series are loaded
│   ├── smard.py      #   API client (retries, throttling) and chunk parsing
│   ├── storage.py    #   Parquet raw layer with idempotent upserts
│   └── ingest.py     #   backfill / update entry point
├── tests/            # unit tests on recorded API responses (no network)
├── data/raw/         # series=<id>/month=<YYYY-MM>.parquet, written by the pipeline
├── dashboard/        # Streamlit app
└── .github/workflows # CI and the daily pipeline run
```

## Quick start

```bash
make install
make test       # 21 unit tests, no network
make backfill   # full history since Oct 2018, ~25 min
make update     # re-load the last two weeks (the daily job)
```

How the loading works:

- **Incremental:** `update` re-loads from two weeks before the newest stored value. That picks up SMARD's late corrections and closes gaps if runs were missed.
- **Idempotent:** writes are upserts on `(series_id, ts_utc)`, so running the same load twice leaves the files byte-identical.
- **Robust:** retries with backoff on transient HTTP errors; one failing series does not stop the others, but the run exits with an error.
- **Time:** everything is stored in UTC at quarter-hour grain. Clock-change weeks (668 / 676 quarter hours) need no special handling that way.

## Data

Source: Bundesnetzagentur | SMARD.de, licensed under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).
