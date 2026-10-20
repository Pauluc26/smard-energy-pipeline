-- Residual load is defined as grid load minus wind and solar. In the history the
-- difference is at most ~4 MWh, so 10 MWh flags a real inconsistency.
select ts_utc, grid_load, wind_onshore, wind_offshore, solar, residual_load
from {{ ref('int_quarter_hours_wide') }}
where abs(residual_load - (grid_load - wind_onshore - wind_offshore - solar)) > 10
