"""Streamlit dashboard: how wind and solar move the German electricity price.

    streamlit run dashboard/app.py

Reads the marts the daily pipeline publishes on the `data` branch. If data/marts
exists locally (after `make pipeline` or `make pull-data`), that is used instead.
"""
import io
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import requests
import streamlit as st
from plotly.subplots import make_subplots

import analysis
import texts

REPO = "Pauluc26/smard-energy-pipeline"
REMOTE = f"https://raw.githubusercontent.com/{REPO}/data/data/marts"
LOCAL = Path(__file__).resolve().parent.parent / "data" / "marts"

st.set_page_config(page_title="Wind, Solar & the Power Price", page_icon="⚡", layout="wide")

# Reference palette, first three categorical slots (validated for colour-blind
# safety as a set) plus a sequential blue; dark-mode steps are chosen separately.
DARK = st.context.theme.type == "dark"
BLUE, ORANGE, AQUA = ("#3987e5", "#d95926", "#199e70") if DARK else ("#2a78d6", "#eb6834", "#1baf7a")
MUTED = "#c3c2b7" if DARK else "#52514e"
ERA_COLOURS = dict(zip(analysis.ERAS, [BLUE, ORANGE, AQUA]))
SEQUENTIAL = ([[0, "#1a1a19"], [1, "#86b6ef"]] if DARK else [[0, "#f4f8fd"], [1, "#104281"]])


@st.cache_data(ttl=3600, show_spinner="Loading data …")
def load(name: str) -> pd.DataFrame:
    local = LOCAL / f"{name}.parquet"
    if local.exists():
        return pd.read_parquet(local)
    response = requests.get(f"{REMOTE}/{name}.parquet", timeout=60)
    response.raise_for_status()
    return pd.read_parquet(io.BytesIO(response.content))


def read_it(tab: str) -> None:
    st.markdown(f"**How to read it:** {texts.TABS[tab]['read']}")


def judge_it(tab: str) -> None:
    with st.expander("What is good, what is bad?"):
        st.markdown(texts.TABS[tab]["judge"])


def show(fig: go.Figure, height: int = 420) -> None:
    fig.update_layout(height=height, margin=dict(l=10, r=10, t=30, b=10),
                      legend=dict(orientation="h", y=1.12, x=1, xanchor="right"), hovermode="closest")
    st.plotly_chart(fig, width="stretch", theme="streamlit", config={"displayModeBar": False})


hours = analysis.prepare_hours(load("fct_hours"))
quarter_hours = load("fct_quarter_hours")
days = load("fct_days")

# --- header ---------------------------------------------------------------------------
latest = pd.Timestamp(quarter_hours["ts_utc"].max()).tz_convert("Europe/Berlin")
st.title("How wind and solar move the German power price")
st.markdown(
    "**How much do wind and solar push down the day-ahead price, and when do they push it below zero?** "
    f"Data from SMARD (Bundesnetzagentur), updated daily. Prices up to {latest:%d %b %Y, %H:%M}."
)

# --- the basics in three boxes, plus a glossary ---------------------------------------
for col, (title, body) in zip(st.columns(3), texts.INTRO):
    with col.container(border=True):
        st.markdown(f"**{title}**")
        st.markdown(body)
with st.expander("Glossary: units and terms used on this page"):
    st.markdown(texts.GLOSSARY)

# --- key figures ----------------------------------------------------------------------
yearly = analysis.yearly_summary(hours)
this_year = latest.year
last_day_of_year = latest.dayofyear
ytd = hours[(hours["year"] == this_year)]
ytd_last = hours[(hours["year"] == this_year - 1) & (hours["date_local"].dt.dayofyear <= last_day_of_year)]
recent_30 = hours[hours["date_local"] > hours["date_local"].max() - pd.Timedelta(days=30)].dropna(
    subset=["generation_wind", "generation_solar", "grid_load"])
today = days.sort_values("date_local").iloc[-1]

c1, c2, c3, c4 = st.columns(4)
avg_30 = days[pd.to_datetime(days.date_local) > pd.to_datetime(today.date_local) - pd.Timedelta(days=30)].price_base.mean()
c1.metric(f"Price {pd.Timestamp(today.date_local):%d %b}, €/MWh", f"{today.price_base:.0f}",
          f"{today.price_base - avg_30:+.0f} vs. 30-day average", delta_color="inverse",
          help=f"Average day-ahead price over all hours of the newest day. The 30-day average is "
               f"{avg_30:.0f} €/MWh. Green = cheaper than usual (good for buyers), red = more expensive "
               "(good for producers). 100 €/MWh = 10 cent per kWh wholesale.")
neg_now, neg_before = int((ytd.price_day_ahead < 0).sum()), int((ytd_last.price_day_ahead < 0).sum())
c2.metric(f"Negative hours {this_year}", f"{neg_now}", f"{neg_now - neg_before:+d} vs. {this_year - 1}",
          delta_color="off", help=f"Hours with a negative price so far this year, compared with the same "
                                  f"period of {this_year - 1}. Neither good nor bad in itself: more renewables, "
                                  "but also too little flexibility to use them (see 'When').")
c3.metric("Wind + solar, 30 days",
          f"{(recent_30.generation_wind.sum() + recent_30.generation_solar.sum()) / recent_30.grid_load.sum():.0%}",
          help="Wind and solar generation as a share of consumption over the last 30 days. Higher means "
               "less fuel and CO₂; it varies strongly with season and weather.")
c4.metric("Tipping point", "≈ 80 %", help="Above a wind + solar share of about 80 % of consumption, "
          "negative prices become common (see 'Tipping point')")

# --- filter row -----------------------------------------------------------------------
years = sorted(hours["year"].unique())
first, last = st.select_slider("Years for 'Tipping point' and 'When'", options=years,
                               value=(2023, years[-1]))
selected = hours[hours["year"].between(first, last)]

trend, tipping, merit, when, recent = st.tabs(
    ["Trend", "Tipping point", "Merit order", "When", "Last 7 days"])

# --- 1. trend -------------------------------------------------------------------------
with trend:
    read_it("trend")
    labels = [f"{y}*" if partial else str(y) for y, partial in zip(yearly.index, yearly.is_partial)]
    left, right = st.columns(2)
    with left:
        fig = go.Figure(go.Bar(x=labels, y=yearly.negative_hours, marker_color=BLUE,
                               text=yearly.negative_hours, textposition="outside",
                               hovertemplate="%{x}: %{y} hours<extra></extra>"))
        fig.update_layout(title="Hours with a negative price", yaxis_title="hours", xaxis_type="category")
        show(fig)
    with right:
        fig = go.Figure(go.Scatter(x=labels, y=yearly.renewable_share * 100, mode="lines+markers",
                                   line=dict(color=AQUA, width=2), marker=dict(size=8),
                                   hovertemplate="%{x}: %{y:.0f} %<extra></extra>"))
        fig.update_layout(title="Renewable share of consumption", yaxis_title="%", yaxis_range=[0, 100],
                          xaxis_type="category")
        show(fig)
    fig = go.Figure(go.Bar(x=labels, y=yearly.avg_price, marker_color=MUTED,
                           hovertemplate="%{x}: %{y:.0f} €/MWh<extra></extra>"))
    fig.update_layout(title="Average day-ahead price", yaxis_title="€/MWh", xaxis_type="category")
    show(fig, height=300)
    st.caption("\\* partial year. Negative hours follow the renewable share. The price level does not: "
               "2022 averaged 235 €/MWh at the same renewable share as 2020 (30 €/MWh). That is the gas crisis.")

    judge_it("trend")

# --- 2. tipping point -----------------------------------------------------------------
with tipping:
    read_it("tipping")
    prob = analysis.negative_probability(selected)
    fig = go.Figure(go.Scatter(
        x=prob.wind_solar_share * 100, y=prob.share_negative * 100, mode="lines+markers",
        line=dict(color=BLUE, width=2), marker=dict(size=9, line=dict(width=2, color="white")),
        customdata=prob[["hours", "median_price"]],
        hovertemplate=("wind + solar ≈ %{x:.0f} % of load<br>negative in %{y:.1f} % of hours<br>"
                       "median price %{customdata[1]:.0f} €/MWh<br>%{customdata[0]:,} hours<extra></extra>")))
    fig.update_layout(title=f"Probability of a negative price ({first}–{last})",
                      xaxis_title="wind + solar generation as share of consumption (%)",
                      yaxis_title="hours with negative price (%)", yaxis_range=[0, 100])
    show(fig)
    st.caption("Below about 60 % the price is practically never negative. Once wind and solar cover most "
               "of the load, plants that cannot ramp down and subsidised generation push it below zero.")

    judge_it("tipping")

# --- 3. merit order -------------------------------------------------------------------
with merit:
    read_it("merit")
    curve = analysis.merit_order(hours)
    fig = go.Figure()
    for era, d in curve.groupby("era", sort=False):
        fig.add_trace(go.Scatter(x=d.residual_gw, y=d.median_price, name=era, mode="lines+markers",
                                 line=dict(color=ERA_COLOURS[era], width=2), marker=dict(size=8),
                                 hovertemplate=f"{era}<br>%{{x:.0f}} GW residual load<br>"
                                               "median %{y:.0f} €/MWh<extra></extra>"))
    fig.add_hline(y=0, line_color=MUTED, line_width=1)
    fig.update_layout(title="Median price by residual load (consumption minus wind and solar)",
                      xaxis_title="residual load (GW)", yaxis_title="€/MWh")
    show(fig)
    effect = analysis.effect_by_period(hours)
    cols = st.columns(len(effect))
    for col, row in zip(cols, effect.itertuples()):
        col.metric(f"Effect of +10 pp wind + solar, {row.era}", f"{row.effect_per_10pp:.0f} €/MWh",
                   help=f"Within calendar months; average price {row.avg_price:.0f} €/MWh, "
                        f"correlation {row.correlation:.2f}")
    st.caption("Wind and solar move the market along the curve; fuel prices move the curve itself. "
               "That is why the same extra wind saved far more during the gas crisis. Estimates compare "
               "hours within the same month and are descriptive, not causal.")

    judge_it("merit")

# --- 4. when --------------------------------------------------------------------------
with when:
    read_it("when")
    grid = analysis.negative_heatmap(selected)
    months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    fig = go.Figure(go.Heatmap(z=grid.values, x=months, y=[f"{h:02d}:00" for h in grid.index],
                               colorscale=SEQUENTIAL, xgap=2, ygap=2, colorbar=dict(title="hours"),
                               hovertemplate="%{x}, %{y}: %{z} negative hours<extra></extra>"))
    fig.update_layout(title=f"Negative-price hours by hour of day and month ({first}–{last})",
                      yaxis_autorange="reversed")
    show(fig, height=560)
    weekend = selected.groupby("is_weekend")["price_day_ahead"].apply(lambda p: (p < 0).mean())
    st.caption(f"Negative prices are a solar phenomenon: midday, spring and summer. Weekends: "
               f"{weekend.get(True, 0):.1%} of hours negative, weekdays {weekend.get(False, 0):.1%}.")

    judge_it("when")

# --- 5. last 7 days -------------------------------------------------------------------
with recent:
    read_it("recent")
    start = quarter_hours["ts_utc"].max() - pd.Timedelta(days=7)
    week = quarter_hours[quarter_hours["ts_utc"] > start].copy()
    week["time"] = week["ts_utc"].dt.tz_convert("Europe/Berlin")
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.08, row_heights=[0.45, 0.55],
                        subplot_titles=("Day-ahead price (€/MWh)", "Generation and load (GW)"))
    fig.add_trace(go.Scatter(x=week.time, y=week.price_day_ahead, name="price", line=dict(color=MUTED, width=1.5),
                             hovertemplate="%{x|%a %d %b %H:%M}: %{y:.1f} €/MWh<extra></extra>"), row=1, col=1)
    fig.add_hline(y=0, line_color=MUTED, line_width=1, line_dash="dot", row=1, col=1)
    to_gw = 4 / 1000  # MWh per quarter hour -> average GW
    for name, column, colour in [("wind", ["wind_onshore", "wind_offshore"], BLUE), ("solar", ["solar"], ORANGE)]:
        fig.add_trace(go.Scatter(x=week.time, y=week[column].sum(axis=1, min_count=len(column)) * to_gw,
                                 name=name, stackgroup="gen", line=dict(color=colour, width=0.5),
                                 hovertemplate=f"{name}: %{{y:.1f}} GW<extra></extra>"), row=2, col=1)
    fig.add_trace(go.Scatter(x=week.time, y=week.grid_load * to_gw, name="consumption",
                             line=dict(color=AQUA, width=2),
                             hovertemplate="consumption: %{y:.1f} GW<extra></extra>"), row=2, col=1)
    show(fig, height=600)
    hidden = analysis.hidden_negative_events(quarter_hours)
    st.caption(f"Quarter-hour prices since October 2025. {hidden['with_negative_quarter_hour']} hours had at "
               f"least one negative quarter hour, but only {hidden['negative_on_average']} were negative on "
               f"average: an hourly view misses {hidden['missed_by_hourly_view']} of them. Actual generation "
               "is published with about one hour delay, so the newest hours show prices only.")

    judge_it("recent")

# --- footer ---------------------------------------------------------------------------
with st.expander("Method and limitations"):
    st.markdown("""
- **No gas or CO₂ prices.** They set the price level; the renewable effect is therefore shown per period, not as one number.
- **Descriptive, not causal.** The effect compares hours within the same month; weekday and holiday patterns are not controlled for.
- **No imports and exports.** A wind + solar share above 100 % means Germany exports or curtails.
- **Quarter-hour prices** exist since 1 October 2025; before, each hourly price applied to all four quarter hours. Long-term views therefore use hours.
- Pipeline, tests and code: [github.com/Pauluc26/smard-energy-pipeline](https://github.com/Pauluc26/smard-energy-pipeline)
""")
st.caption("Source: Bundesnetzagentur | SMARD.de, licensed under CC BY 4.0.")
