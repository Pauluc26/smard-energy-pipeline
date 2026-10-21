"""Calculations behind the dashboard. Pure pandas, no Streamlit, so they can be tested.

The same analyses are explained step by step in notebooks/01_explore.ipynb.
"""
import numpy as np
import pandas as pd

# Periods with clearly different fuel-price levels (gas crisis in 2021-2022)
ERAS = {"2018–2020": (2018, 2020), "2021–2022": (2021, 2022), "2023–today": (2023, 2100)}


def prepare_hours(hours: pd.DataFrame) -> pd.DataFrame:
    """Add the columns the views need. Keeps hours without biomass data (it lags ~4 days)."""
    out = hours.copy()
    out["date_local"] = pd.to_datetime(out["date_local"])
    out["year"] = out["date_local"].dt.year
    out["month"] = out["date_local"].dt.month
    out["is_weekend"] = out["date_local"].dt.dayofweek >= 5
    out["wind_solar_share"] = (out["generation_wind"] + out["generation_solar"]) / out["grid_load"]
    out["residual_gw"] = out["residual_load"] / 1000  # MWh per hour = average MW -> GW
    return out


def yearly_summary(hours: pd.DataFrame) -> pd.DataFrame:
    """Per year: average price, hours with a negative price, renewable share of load."""
    complete = hours[hours["is_complete"]]
    out = hours.groupby("year").agg(
        avg_price=("price_day_ahead", "mean"),
        negative_hours=("price_day_ahead", lambda p: int((p < 0).sum())),
    )
    shares = complete.groupby("year")[["generation_renewable", "grid_load"]].sum()
    out["renewable_share"] = shares["generation_renewable"] / shares["grid_load"]
    last_day = hours["date_local"].max()
    out["is_partial"] = out.index == last_day.year
    out.loc[out.index == hours["date_local"].min().year, "is_partial"] = True  # history starts in October 2018
    return out


def negative_probability(hours: pd.DataFrame, step: float = 0.1, min_hours: int = 100) -> pd.DataFrame:
    """Share of hours with a negative price, by wind + solar share of load."""
    data = hours.dropna(subset=["wind_solar_share", "price_day_ahead"])
    edges = np.arange(0, data["wind_solar_share"].max() + step, step)
    bins = pd.cut(data["wind_solar_share"], edges)
    out = data.groupby(bins, observed=True).agg(
        hours=("price_day_ahead", "size"),
        share_negative=("price_day_ahead", lambda p: (p < 0).mean()),
        median_price=("price_day_ahead", "median"),
    )
    out = out[out["hours"] >= min_hours]
    out.index = [iv.mid for iv in out.index]
    out.index.name = "wind_solar_share"
    return out.reset_index()


def merit_order(hours: pd.DataFrame, step_gw: float = 10, min_hours: int = 50) -> pd.DataFrame:
    """Median price by residual-load band, per period (long format)."""
    data = hours.dropna(subset=["residual_gw", "price_day_ahead"])
    edges = np.arange(np.floor(data["residual_gw"].min() / step_gw) * step_gw,
                      data["residual_gw"].max() + step_gw, step_gw)
    rows = []
    for era, (first, last) in ERAS.items():
        d = data[data["year"].between(first, last)]
        curve = d.groupby(pd.cut(d["residual_gw"], edges), observed=True).agg(
            median_price=("price_day_ahead", "median"), hours=("price_day_ahead", "size"))
        curve = curve[curve["hours"] >= min_hours]
        for interval, row in curve.iterrows():
            rows.append({"era": era, "residual_gw": interval.mid, **row.to_dict()})
    return pd.DataFrame(rows)


def effect_by_period(hours: pd.DataFrame) -> pd.DataFrame:
    """€/MWh price change per +10 percentage points of wind + solar, within calendar months.

    Price and share are de-meaned per month, which removes slow changes like the gas
    price level. Descriptive, not causal: weekday patterns are not controlled for.
    """
    data = hours.dropna(subset=["wind_solar_share", "price_day_ahead"])
    rows = []
    for era, (first, last) in ERAS.items():
        d = data[data["year"].between(first, last)]
        if len(d) < 2:
            continue  # period not covered by the data
        group = d.groupby(["year", "month"])
        y = d["price_day_ahead"] - group["price_day_ahead"].transform("mean")
        x = d["wind_solar_share"] - group["wind_solar_share"].transform("mean")
        rows.append({
            "era": era,
            "effect_per_10pp": (x * y).sum() / (x * x).sum() / 10,
            "correlation": np.corrcoef(x, y)[0, 1],
            "avg_price": d["price_day_ahead"].mean(),
        })
    return pd.DataFrame(rows)


def negative_heatmap(hours: pd.DataFrame) -> pd.DataFrame:
    """Hours with a negative price, hour of day (rows 0-23) x month (columns 1-12)."""
    negative = hours[hours["price_day_ahead"] < 0]
    return (negative.pivot_table(index="hour_of_day_local", columns="month",
                                 values="price_day_ahead", aggfunc="size")
            .reindex(index=range(24), columns=range(1, 13)).fillna(0).astype(int))


def hidden_negative_events(quarter_hours: pd.DataFrame) -> dict:
    """Since quarter-hour prices: hours with a negative quarter hour vs. negative on average."""
    qh = quarter_hours[quarter_hours["has_quarter_hour_price"]]
    by_hour = qh.groupby(qh["ts_utc"].dt.floor("h"))["price_day_ahead"].agg(["mean", "min", "max"])
    with_negative = int((by_hour["min"] < 0).sum())
    negative_on_average = int((by_hour["mean"] < 0).sum())
    return {
        "hours": len(by_hour),
        "with_negative_quarter_hour": with_negative,
        "negative_on_average": negative_on_average,
        "missed_by_hourly_view": with_negative - negative_on_average,
        "median_spread": float((by_hour["max"] - by_hour["min"]).median()),
    }
