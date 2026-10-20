-- Residual load is defined as grid load minus wind and solar. In the history the
-- difference is at most ~4 MWh, so 10 MWh flags a real inconsistency.
-- The newest hours are skipped: SMARD publishes them as provisional values and revises
-- them within minutes, so series loaded a few minutes apart can briefly disagree.
-- They are re-loaded on the next run anyway.
select ts_utc, grid_load, wind_onshore, wind_offshore, solar, residual_load
from {{ ref('int_quarter_hours_wide') }}
where abs(residual_load - (grid_load - wind_onshore - wind_offshore - solar)) > 10
  and ts_utc < now() - interval 3 hour
