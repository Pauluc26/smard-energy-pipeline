-- Hourly aggregates. Comparable over the full history, also across the switch to
-- quarter-hour prices in October 2025. Energy values are MWh per hour.

select
    date_trunc('hour', ts_utc) as hour_utc,
    min(ts_local) as hour_local,
    min(date_local) as date_local,
    min(hour_local) as hour_of_day_local,

    avg(price_day_ahead) as price_day_ahead,
    min(price_day_ahead) as price_min,
    max(price_day_ahead) as price_max,
    count(*) filter (where is_negative_price) as negative_quarter_hours,

    sum(generation_renewable) as generation_renewable,
    sum(generation_conventional) as generation_conventional,
    sum(generation_total) as generation_total,
    sum(wind_onshore + wind_offshore) as generation_wind,
    sum(solar) as generation_solar,
    sum(natural_gas) as generation_gas,
    sum(lignite + hard_coal) as generation_coal,
    sum(grid_load) as grid_load,
    sum(residual_load) as residual_load,
    sum(generation_renewable) / nullif(sum(grid_load), 0) as renewable_share_of_load,

    sum(forecast_wind_solar) as forecast_wind_solar,
    sum(forecast_total) as forecast_total,

    count(*) as quarter_hours,
    bool_and(is_complete) and count(*) = 4 as is_complete
from {{ ref('fct_quarter_hours') }}
group by date_trunc('hour', ts_utc)
