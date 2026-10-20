-- Daily summary in German local time. A day has 23, 24 or 25 hours (clock change).
-- Energy values are GWh per day.

select
    date_local,
    avg(price_day_ahead) as price_base,  -- average over all hours ("baseload")
    -- exchange definition of "peak": 08:00-20:00 on weekdays, so null on weekends
    avg(price_day_ahead) filter (where hour_of_day_local between 8 and 19 and isodow(date_local) <= 5)
        as price_peak,
    min(price_day_ahead) as price_min_hour,
    max(price_day_ahead) as price_max_hour,
    count(*) filter (where price_day_ahead < 0) as negative_price_hours,

    sum(generation_renewable) / 1000 as generation_renewable_gwh,
    sum(generation_wind) / 1000 as generation_wind_gwh,
    sum(generation_solar) / 1000 as generation_solar_gwh,
    sum(generation_gas) / 1000 as generation_gas_gwh,
    sum(generation_coal) / 1000 as generation_coal_gwh,
    sum(grid_load) / 1000 as grid_load_gwh,
    sum(generation_renewable) / nullif(sum(grid_load), 0) as renewable_share_of_load,

    count(*) as hours,
    bool_and(is_complete) as is_complete
from {{ ref('fct_hours') }}
group by date_local
