{#
    Generic data tests. Each returns the rows that violate the rule; dbt fails the
    test if any rows come back. Thresholds per series live in seeds/series.csv.
#}

{% test unique_combination(model, columns) %}
select {{ columns | join(', ') }}, count(*) as n
from {{ model }}
group by {{ columns | join(', ') }}
having count(*) > 1
{% endtest %}


{# Physically plausible range per series. Catches unit mix-ups (MW vs. MWh) and broken values. #}
{% test value_within_series_range(model) %}
select o.series_id, o.ts_utc, o.value, s.min_value, s.max_value
from {{ model }} as o
inner join {{ ref('series') }} as s using (series_id)
where o.value < s.min_value or o.value > s.max_value
{% endtest %}


{# Rows must follow each other in exact 15-minute steps (in UTC there is no clock change). #}
{% test no_gaps_in_time_axis(model) %}
with steps as (
    select
        series_id,
        ts_utc,
        ts_utc - lag(ts_utc) over (partition by series_id order by ts_utc) as step
    from {{ model }}
)
select * from steps
where step is not null and step <> interval 15 minute
{% endtest %}


{# Each live series must have data newer than its allowed publication lag. #}
{% test series_is_fresh(model) %}
with latest as (
    select series_id, max(ts_utc) as latest_ts
    from {{ model }}
    group by series_id
)
select s.series_id, s.name, l.latest_ts, s.max_lag_hours
from {{ ref('series') }} as s
left join latest as l using (series_id)
where s.ended_on is null
  and (l.latest_ts is null or l.latest_ts < now() - to_hours(s.max_lag_hours::integer))
{% endtest %}
