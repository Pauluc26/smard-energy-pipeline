-- SMARD's forecasts are consistent: wind onshore + wind offshore + solar = wind + solar,
-- and wind + solar + other = total. Allow 1 MWh for rounding.
-- Like the residual-load check, the newest hours are skipped because forecasts can be
-- updated between loading one series and the next.
select ts_utc, forecast_wind_onshore, forecast_wind_offshore, forecast_solar,
       forecast_wind_solar, forecast_other, forecast_total
from {{ ref('int_quarter_hours_wide') }}
where (abs(forecast_wind_onshore + forecast_wind_offshore + forecast_solar - forecast_wind_solar) > 1
       or abs(forecast_wind_solar + forecast_other - forecast_total) > 1)
  and ts_utc < now() - interval 3 hour
