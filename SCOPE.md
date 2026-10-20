# Scope

Defined before building and only changed deliberately, to keep the project focused. The Olist project showed analysis and modelling; this one is about **data engineering**: getting live data in reliably, keeping it correct and keeping it up to date without manual work.

## Goal

A pipeline that pulls German electricity market data from SMARD (Bundesnetzagentur) every day, stores it in a tested, layered DuckDB model and feeds a small public dashboard that answers one question:

> **How much do wind and solar push down the German day-ahead price, and when do they push it below zero?**

## Decisions

- Data source: SMARD chart data API (`www.smard.de/app/chart_data/...`), licence CC BY 4.0. Verified API facts: `docs/api_notes.md`
- Language: English
- Storage grain: quarter hour, timestamps in UTC; conversion to Europe/Berlin only in the marts and the dashboard
- History: from 1 October 2018 (start of the DE-LU bidding zone), so the price series is consistent
- Raw layer: Parquet files, partitioned by series and month. They live on a separate `data` branch that the daily job force-pushes as a single commit, together with the exported marts. (Committing them to `main` was the first plan, but the current month's files change daily: ~1 MB of new history per day, 300–400 MB per year.)
- Transformation: dbt with DuckDB (`dbt-duckdb`), layers `staging → intermediate → marts`
- Orchestration: GitHub Actions, daily at 05:00 UTC plus manual trigger. Data is only published when all tests pass; a failed day heals itself on the next run
- Dashboard: Streamlit, deployed on Streamlit Community Cloud, reading the exported marts (Parquet) from the `data` branch
- Python 3.12, one-command workflow via `make`

## In scope

- Series (region `DE`):
  - Day-ahead price DE-LU (filter 4169)
  - Generation by source: lignite, hard coal, natural gas, nuclear, biomass, hydro, wind onshore, wind offshore, photovoltaics, pumped storage, other renewables, other conventional (1223–1228, 4066–4071)
  - Grid load (410) and residual load (4359)
  - Day-ahead generation forecasts: wind onshore (123), wind offshore (3791), photovoltaics (125), wind + PV (5097), other (715), total (122). These are what the market knows the day before, so the forecast step uses them instead of actual generation (no look-ahead)
- Incremental, idempotent loading: on every run, re-load the last two weekly chunks and overwrite them, so late corrections by SMARD are picked up and repeated runs give the same result
- Handling of the known traps: daylight-saving weeks (668/676 quarter hours instead of 672), trailing `null` values for future slots, the switch from hourly to 15-minute prices on 1 October 2025
- Data-quality checks: dbt tests (unique and not-null keys, value ranges, no gaps in the time axis, freshness) and a run that fails visibly when they break
- Unit tests for the ingestion code with recorded API responses (no network in CI)
- Dashboard: price vs. renewable share, merit-order view, negative-price hours over time
- Optional, only after everything above works: a simple next-day price forecast against a naive baseline (same quarter hour last week), using only the forecast series as inputs

## Known limitation

Gas usually sets the German electricity price (merit order), and gas and CO₂ prices are not in SMARD. Without them, renewables explain price swings **within days and weeks** well, but not the **price level across years** (e.g. 2022). The dashboard says this openly.

## Open: possible extensions

Checked only after the core pipeline runs, and added only with a deliberate scope change:

- **Gas price (priority):** look for a free, daily, licence-compatible source (e.g. Dutch TTF day-ahead). Would remove the main limitation above
- **Weather** (Open-Meteo): a second source with a different grain, mainly as an engineering exercise

## Deliberately out of scope

- Other data sources than SMARD (except the extensions above)
- Other countries, control areas or the intraday market
- SMARD's own forecast series
- Heavy infrastructure: Airflow, Kafka, Docker, cloud warehouses, Terraform
- Real-time or sub-daily updates
- Complex forecasting models (deep learning, hyperparameter searches)
