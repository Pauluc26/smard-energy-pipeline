"""The SMARD series this pipeline loads. Filter IDs are verified in docs/api_notes.md."""
from datetime import datetime, timezone

REGION = "DE"
RESOLUTION = "quarterhour"

# First weekly chunk to load: the week of 1 October 2018, when the DE-LU bidding zone
# started. Chunks begin Monday 00:00 German time, which is Sunday 22:00 UTC in summer.
HISTORY_START = datetime(2018, 9, 30, 22, 0, tzinfo=timezone.utc)

# filter id -> (name, category)
SERIES: dict[int, tuple[str, str]] = {
    4169: ("price_day_ahead", "price"),
    1223: ("lignite", "generation"),
    1224: ("nuclear", "generation"),
    1225: ("wind_offshore", "generation"),
    1226: ("hydro", "generation"),
    1227: ("other_conventional", "generation"),
    1228: ("other_renewables", "generation"),
    4066: ("biomass", "generation"),
    4067: ("wind_onshore", "generation"),
    4068: ("solar", "generation"),
    4069: ("hard_coal", "generation"),
    4070: ("pumped_storage", "generation"),
    4071: ("natural_gas", "generation"),
    410: ("grid_load", "consumption"),
    4359: ("residual_load", "consumption"),
    123: ("forecast_wind_onshore", "forecast"),
    3791: ("forecast_wind_offshore", "forecast"),
    125: ("forecast_solar", "forecast"),
    5097: ("forecast_wind_solar", "forecast"),
    715: ("forecast_other", "forecast"),
    122: ("forecast_total", "forecast"),
}
