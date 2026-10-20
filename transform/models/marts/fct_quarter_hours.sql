-- Quarter-hour fact table: price, generation mix, load and forecasts, with German local time.
-- Energy values are MWh per quarter hour.

with base as (
    select * from {{ ref('int_quarter_hours_wide') }}
),

derived as (
    select
        *,
        wind_onshore + wind_offshore + solar + biomass + hydro + other_renewables
            as generation_renewable,
        lignite + hard_coal + natural_gas + nuclear + pumped_storage + other_conventional
            as generation_conventional
    from base
)

select
    ts_utc,
    timezone('Europe/Berlin', ts_utc) as ts_local,
    timezone('Europe/Berlin', ts_utc)::date as date_local,
    hour(timezone('Europe/Berlin', ts_utc)) as hour_local,

    price_day_ahead,
    price_day_ahead < 0 as is_negative_price,
    -- before 1 Oct 2025 the market traded hours; each hourly price is repeated 4 times
    timezone('Europe/Berlin', ts_utc)::date >= date '{{ var("quarter_hour_prices_from") }}'
        as has_quarter_hour_price,

    lignite, hard_coal, natural_gas, nuclear, pumped_storage, other_conventional,
    wind_onshore, wind_offshore, solar, biomass, hydro, other_renewables,
    generation_renewable,
    generation_conventional,
    generation_renewable + generation_conventional as generation_total,

    grid_load,
    residual_load,
    -- can exceed 1 when Germany exports renewable power
    generation_renewable / nullif(grid_load, 0) as renewable_share_of_load,
    (wind_onshore + wind_offshore + solar) / nullif(grid_load, 0) as wind_solar_share_of_load,

    forecast_wind_onshore, forecast_wind_offshore, forecast_solar,
    forecast_wind_solar, forecast_other, forecast_total,

    -- all actuals published (the newest hours have prices and forecasts, but no actuals yet)
    generation_renewable is not null
        and generation_conventional is not null
        and grid_load is not null as is_complete
from derived
