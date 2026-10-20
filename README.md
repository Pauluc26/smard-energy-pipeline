# SMARD Energy Pipeline

[![pipeline](https://github.com/Pauluc26/smard-energy-pipeline/actions/workflows/pipeline.yml/badge.svg)](https://github.com/Pauluc26/smard-energy-pipeline/actions/workflows/pipeline.yml)
[![tests](https://github.com/Pauluc26/smard-energy-pipeline/actions/workflows/tests.yml/badge.svg)](https://github.com/Pauluc26/smard-energy-pipeline/actions/workflows/tests.yml)

> Work in progress. Scope and decisions: [`SCOPE.md`](SCOPE.md).

A daily-updating data pipeline for the German electricity market. It pulls generation by source, consumption and day-ahead prices from [SMARD](https://www.smard.de) (Bundesnetzagentur), models them in DuckDB with dbt and feeds a dashboard that asks: **how much do wind and solar push down the electricity price, and when do they push it below zero?**

## Planned architecture

```
SMARD API ──► src/ingest (Python) ──► data/raw/*.parquet ──► dbt + DuckDB ──► data/marts/*.parquet ──► dashboard
                                              │                       │ 27 tests            │
                                              └────────── data branch (one commit, force-pushed) ┘
                         GitHub Actions runs all of it daily at 05:00 UTC
```

The daily job (`.github/workflows/pipeline.yml`): pull the stored data from the `data` branch → load new data → build and test the models → export the marts → publish. Nothing is published if a test fails, and the next run re-loads the missed days.

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
├── transform/        # dbt project (DuckDB)
│   ├── seeds/series.csv   # series metadata + data-quality thresholds (shared with src/)
│   ├── models/            #   staging → intermediate → marts (quarter hour, hour, day)
│   └── tests/             #   data tests (gaps, ranges, freshness, physical identities)
├── scripts/data_branch.sh  # pull / push the data branch
├── notebooks/01_explore.ipynb  # exploration: finding the story for the dashboard
├── tests/            # unit tests on recorded API responses (no network)
├── data/raw/         # series=<id>/month=<YYYY-MM>.parquet, written by the pipeline
├── dashboard/        # Streamlit app
└── .github/workflows # CI and the daily pipeline run
```

## Quick start

```bash
make install
make pull-data  # get the published data (instead of a 25-min backfill)
make test       # 21 unit tests, no network
make backfill   # or: full history from SMARD since Oct 2018, ~25 min
make update     # re-load the last two weeks
make transform  # dbt: build the models and run 27 data tests (~10 s)
make export     # marts as Parquet for the dashboard
```

How the loading works:

- **Incremental:** `update` re-loads from two weeks before the newest stored value. That picks up SMARD's late corrections and closes gaps if runs were missed.
- **Idempotent:** writes are upserts on `(series_id, ts_utc)`, so running the same load twice leaves the files byte-identical.
- **Robust:** retries with backoff on transient HTTP errors; one failing series does not stop the others, but the run exits with an error.
- **Tested data:** dbt checks uniqueness, a gap-free 15-minute axis, plausible ranges and freshness per series, and two physical identities (forecast parts add up to the total; residual load = load − wind − solar).
- **Time:** everything is stored in UTC at quarter-hour grain. Clock-change weeks (668 / 676 quarter hours) need no special handling that way. The DuckDB session is pinned to UTC too, otherwise `date_trunc` follows the machine's time zone and results differ between a laptop and CI.

## Data

Source: Bundesnetzagentur | SMARD.de, licensed under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).
