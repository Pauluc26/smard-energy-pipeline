-- One row per quarter hour on a complete time axis, one column per series.
-- The axis runs from the start of the history to the newest price, so quarter hours
-- with missing data show up as nulls instead of silently disappearing.

{% set series_names = [
    'price_day_ahead',
    'lignite', 'nuclear', 'wind_offshore', 'hydro', 'other_conventional', 'other_renewables',
    'biomass', 'wind_onshore', 'solar', 'hard_coal', 'pumped_storage', 'natural_gas',
    'grid_load', 'residual_load',
    'forecast_wind_onshore', 'forecast_wind_offshore', 'forecast_solar',
    'forecast_wind_solar', 'forecast_other', 'forecast_total',
] %}

with observations as (
    select * from {{ ref('stg_smard__observations') }}
),

bounds as (
    select min(ts_utc) as first_ts, max(ts_utc) as last_ts
    from observations
    where series_name = 'price_day_ahead'
),

spine as (
    select unnest(generate_series(first_ts, last_ts, interval 15 minute)) as ts_utc
    from bounds
),

wide as (
    select
        ts_utc,
        {% for name in series_names %}
        max(value) filter (where series_name = '{{ name }}') as {{ name }}{{ ',' if not loop.last }}
        {% endfor %}
    from observations
    group by ts_utc
),

nuclear_end as (
    select max(ts_utc) as last_ts
    from observations
    where series_name = 'nuclear'
)

select
    spine.ts_utc,
    {% for name in series_names %}
    {% if name == 'nuclear' %}
    -- the series stops after the phase-out (April 2023, reported as 0 until Jan 2024)
    case when spine.ts_utc > nuclear_end.last_ts then 0 else wide.nuclear end as nuclear,
    {% else %}
    wide.{{ name }},
    {% endif %}
    {% endfor %}
from spine
cross join nuclear_end
left join wide using (ts_utc)
