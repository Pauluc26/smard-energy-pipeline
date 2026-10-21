"""Unit tests for the dashboard calculations, on small hand-made frames."""
import numpy as np
import pandas as pd
import pytest

from dashboard import analysis


def make_hours(prices, wind=0.0, solar=0.0, load=1000.0, start="2024-05-01", residual=None):
    n = len(prices)
    dates = pd.date_range(start, periods=n, freq="h")
    frame = pd.DataFrame({
        "date_local": dates.normalize(),
        "hour_of_day_local": dates.hour,
        "price_day_ahead": prices,
        "generation_wind": wind,
        "generation_solar": solar,
        "generation_renewable": np.asarray(wind) + np.asarray(solar),
        "grid_load": load,
        "residual_load": residual if residual is not None else np.asarray(load) - np.asarray(wind) - np.asarray(solar),
        "is_complete": True,
    })
    return analysis.prepare_hours(frame)


def test_prepare_hours_adds_share_and_weekend():
    hours = make_hours([10.0, 20.0], wind=[300, 600], solar=[100, 300], start="2024-05-04")  # a Saturday
    assert hours["wind_solar_share"].tolist() == pytest.approx([0.4, 0.9])
    assert hours["is_weekend"].all()


def test_yearly_summary_counts_negative_hours_and_flags_partial_years():
    hours = pd.concat([make_hours([-1.0, 5.0], start="2023-06-01"), make_hours([-2.0, -3.0, 4.0], start="2024-06-01")])
    yearly = analysis.yearly_summary(hours)
    assert yearly["negative_hours"].tolist() == [1, 2]
    assert yearly["is_partial"].tolist() == [True, True]  # first and last year


def test_negative_probability_by_share_band():
    # 100 hours at 85 % share, a quarter of them negative; 100 hours at 25 %, none negative
    prices = [-1.0] * 25 + [50.0] * 75 + [80.0] * 100
    wind = [850.0] * 100 + [250.0] * 100
    prob = analysis.negative_probability(make_hours(prices, wind=wind), min_hours=50)
    assert prob["wind_solar_share"].tolist() == pytest.approx([0.25, 0.85])
    assert prob["share_negative"].tolist() == pytest.approx([0.0, 0.25])


def test_negative_probability_drops_thin_bands():
    prob = analysis.negative_probability(make_hours([-1.0] * 10, wind=[950.0] * 10), min_hours=50)
    assert prob.empty


def test_effect_by_period_recovers_a_known_slope():
    # within one month: price = 100 - 200 * share, i.e. -20 €/MWh per +10 pp
    rng = np.random.default_rng(0)
    share = rng.uniform(0.1, 0.9, 500)
    hours = make_hours(100 - 200 * share, wind=share * 1000, start="2024-05-01")
    effect = analysis.effect_by_period(hours).set_index("era")
    assert effect.loc["2023–today", "effect_per_10pp"] == pytest.approx(-20)


def test_negative_heatmap_has_full_grid():
    grid = analysis.negative_heatmap(make_hours([-1.0, 5.0, -2.0]))
    assert grid.shape == (24, 12)
    assert grid.loc[0, 5] == 1 and grid.loc[2, 5] == 1 and grid.values.sum() == 2


def test_hidden_negative_events_counts_quarter_hours_hidden_by_hourly_average():
    ts = pd.date_range("2025-11-03 10:00", periods=8, freq="15min", tz="UTC")
    qh = pd.DataFrame({
        "ts_utc": ts,
        "price_day_ahead": [-5.0, 10.0, 10.0, 10.0,   # hour 1: one negative quarter hour, positive average
                            -5.0, -5.0, -5.0, 1.0],   # hour 2: negative on average
        "has_quarter_hour_price": True,
    })
    hidden = analysis.hidden_negative_events(qh)
    assert hidden["with_negative_quarter_hour"] == 2
    assert hidden["negative_on_average"] == 1
    assert hidden["missed_by_hourly_view"] == 1
