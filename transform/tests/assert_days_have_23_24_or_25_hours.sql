-- Every full day in German time has 24 hours, the clock-change days 23 or 25.
-- Guards against time-zone bugs such as truncating timestamps in the machine's
-- local time (see profiles.yml). The newest day may still be partial.
select date_local, hours
from {{ ref('fct_days') }}
where hours not in (23, 24, 25)
  and date_local < (select max(date_local) from {{ ref('fct_days') }})
