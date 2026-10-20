# SMARD API notes

Facts checked against the live API on 2026-10-20. Reference: the OpenAPI spec in [bundesAPI/smard-api](https://github.com/bundesAPI/smard-api), documented at bund.dev.

## Endpoints

Base URL: `https://www.smard.de/app`

| Purpose | Path |
|---|---|
| List of available chunks | `/chart_data/{filter}/{region}/index_{resolution}.json` → `{"timestamps": [...]}` |
| One chunk of data | `/chart_data/{filter}/{region}/{filter}_{region}_{resolution}_{timestamp}.json` → `{"series": [[ts, value], ...]}` |

- No API key. Filter and region appear twice in the chunk path and must match, otherwise 404.
- A timestamp that is not in the index also returns an empty/non-JSON response, so always read the index first.
- Resolutions: `quarterhour`, `hour`, `day`, `week`, `month`, `year`.

## Timestamps and chunks

- Unix epoch in **milliseconds**, UTC.
- One chunk = **one week**, starting Monday 00:00 German time. The chunk start is therefore Sunday 22:00 UTC in summer and 23:00 UTC in winter.
- A normal week has 672 quarter hours. The week with the clock change has 668 (spring) or 676 (autumn).
- The current week's chunk is padded with `null` for slots that have no data yet. Treat trailing `null` as "not yet published", not as missing data.

## Filters used

| Filter | Series |
|---|---|
| 4169 | Day-ahead price DE-LU (€/MWh) |
| 1223 | Lignite |
| 1224 | Nuclear |
| 1225 | Wind offshore |
| 1226 | Hydropower |
| 1227 | Other conventional |
| 1228 | Other renewables |
| 4066 | Biomass |
| 4067 | Wind onshore |
| 4068 | Photovoltaics |
| 4069 | Hard coal |
| 4070 | Pumped storage (generation) |
| 4071 | Natural gas |
| 410 | Grid load (total consumption) |
| 4359 | Residual load |

Generation and consumption values are MWh per interval.

### Forecast series (day-ahead generation forecasts)

| Filter | Series |
|---|---|
| 123 | Forecast wind onshore |
| 3791 | Forecast wind offshore |
| 125 | Forecast photovoltaics (missing from the OpenAPI enum, but works) |
| 5097 | Forecast wind + photovoltaics |
| 715 | Forecast other |
| 122 | Forecast total |

- All available from 2014-12-28, in all resolutions.
- Consistency checked: 123 + 3791 + 125 = 5097 (e.g. 2299.07 + 1585.99 + 0.00 = 3885.06). Usable as a data-quality test.
- Filter 126 is in the enum without a description and returns exactly −5097. Not used.
- Still to check: at what time of day the forecast for the next day is published (matters for the daily schedule and for the forecast step).

## Coverage (index, quarterhour, region DE)

| Series | First chunk | Note |
|---|---|---|
| Price 4169 | 2018-09-30 22:00 UTC | DE-LU bidding zone starts 1 Oct 2018 |
| Generation / load | 2014-12-28 23:00 UTC | |

## Price resolution switch

The day-ahead market moved from hourly to 15-minute products on **1 October 2025**. In the `quarterhour` series:

- before the switch, each hourly price is repeated four times (e.g. `59.53, 59.53, 59.53, 59.53, 56.10, ...`);
- from the week of 2025-10-05 onward, the four values within an hour differ.

Consequence: hourly aggregates are comparable over the full history; quarter-hour price volatility is only meaningful from October 2025.

## Findings from the first full backfill (2026-10-20, ~22 min, 75 MB Parquet)

- All 21 series complete from 2018-10-01, no duplicates, the time axis is a strict 15-minute grid (668 / 676 quarter hours in clock-change weeks confirmed).
- **Publication lag differs by series.** At 14:30 German time: forecasts and the price ran to the end of the day, actual generation to 13:30, grid load to 13:15, and biomass was 4 days behind. Freshness tests need a threshold per series.
- **Nuclear** is 0 from May 2023 (phase-out on 15 April 2023), and the series stops after January 2024. The marts should treat missing values after that as 0.
- **Residual load** has 3 null quarter hours in the middle of the history: real gaps, kept on purpose.
- Values are MWh **per quarter hour**. Multiply by 4 for average power in MW (e.g. solar peak 14,627 MWh ≈ 58.5 GW).
- The price hits the market floor of −500 €/MWh; 10,161 quarter hours with negative prices since October 2018.
