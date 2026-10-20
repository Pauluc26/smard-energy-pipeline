-- One row per series and quarter hour, enriched with the series metadata.
select
    o.series_id,
    s.name as series_name,
    s.category,
    o.ts_utc,
    o.value
from {{ source('smard', 'observations') }} as o
inner join {{ ref('series') }} as s using (series_id)
