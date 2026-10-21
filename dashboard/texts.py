"""Explanations shown in the dashboard. Kept apart from app.py so the layout code stays readable.

"Good or bad" is deliberately shown from several perspectives: whether a low or
negative price is good depends on who you ask.
"""

INTRO = [
    ("What is the day-ahead price?",
     "Every day at noon, power for each quarter hour of the **next day** is traded on the exchange. "
     "Producers say how much they can deliver at which price, buyers how much they need. "
     "The price where supply meets demand applies to everyone. It is the wholesale price, "
     "before grid fees, taxes and levies."),
    ("Why do wind and solar matter?",
     "Wind and solar cost almost nothing per extra MWh: there is no fuel to pay. "
     "When they produce a lot, the expensive gas and coal plants are not needed, "
     "so the price falls. When there is little wind and sun, the most expensive plant "
     "still needed sets the price for all."),
    ("Is a negative price good or bad?",
     "A negative price means producers **pay** to deliver power. It happens when wind and solar "
     "produce more than can be used and other plants cannot or do not want to switch off. "
     "Good for flexible consumers and storage; costly for producers and for the subsidy account; "
     "a sign that the system lacks flexibility. Details in the tab *When*."),
]

GLOSSARY = """
| Term | Meaning |
|---|---|
| **€/MWh** | Euro per megawatt hour, the unit of the wholesale price. 100 €/MWh = 10 cent per kWh. A household pays roughly three to four times the wholesale price, because grid fees, taxes and levies come on top. |
| **MWh, GWh** | Energy. 1 MWh = 1,000 kWh, about what a German household uses in four months. 1 GWh = 1,000 MWh. |
| **GW** | Power, i.e. energy per hour. Germany consumes about 30–80 GW at any moment, depending on time of day and season. |
| **Consumption (grid load)** | All electricity taken from the public grid in Germany. |
| **Wind + solar share** | Wind and solar generation divided by consumption. Above 100 % Germany produces more than it uses and exports or curtails. |
| **Renewable share** | Like above, but also counting biomass, hydro and other renewables. |
| **Residual load** | Consumption minus wind and solar: what other power plants (gas, coal, biomass, imports, storage) still have to cover. Low residual load = lots of wind and sun. |
| **Merit order** | Power plants are used from cheapest to most expensive. The last plant needed sets the price for everyone. |
| **Negative price** | Producers pay buyers to take power. Mostly at sunny midday hours with low demand. |
| **Quarter-hour price** | Since 1 October 2025 the day-ahead market trades 15-minute blocks instead of hours, so prices can change within an hour. |
| **pp (percentage points)** | The difference between two percentages, e.g. from 50 % to 60 % is +10 pp. |
"""

TABS = {
    "trend": {
        "read": "Each bar is one year. Left: how many hours the price was below zero. Right: how much of "
                "consumption came from renewables. Bottom: the average price.",
        "judge": """
- **Negative hours rising** shows that renewables increasingly cover the whole demand at times. That is a sign of progress in the energy transition, and also a sign that storage, flexible demand and grids are not keeping up.
- **A higher renewable share** means less fuel burnt and less CO₂, and less dependence on gas imports.
- **The average price** depends mostly on gas prices, not only on renewables: compare 2020 (30 €/MWh) with 2022 (235 €/MWh) at the same renewable share. For consumers, lower is better; for producers, higher.
""",
    },
    "tipping": {
        "read": "Each point groups all hours with a similar wind + solar share. The height shows how often "
                "the price was negative in those hours. Use the year slider above to compare periods.",
        "judge": """
- **The curve is flat at zero up to ~60 %:** in normal hours renewables lower the price but do not push it below zero.
- **It rises steeply above ~80 %:** when wind and solar nearly cover the whole demand, there is not enough room for them, and inflexible plants keep running.
- **Good or bad?** The steep part is where cheap power is "wasted". More batteries, electric cars and heat pumps that charge at these times, and more export capacity, would flatten it. A curve that moves to the right over the years would mean the system is becoming more flexible.
""",
    },
    "merit": {
        "read": "Each line is one period. Left: hours with a lot of wind and sun (low residual load). "
                "Right: hours where gas and coal plants must cover most of the demand. Higher line = more "
                "expensive power at the same situation.",
        "judge": """
- **The slope** shows the merit order: the more conventional plants are needed, the more expensive it gets.
- **The height** shows the fuel price level. The 2021–2022 line (gas crisis) is far above 2018–2020.
- **The effect per +10 pp** is how much the price falls when wind and solar cover 10 percentage points more of demand, comparing hours within the same month. It was largest during the gas crisis: every MWh of wind then replaced a very expensive MWh of gas. For consumers this is the "insurance" value of renewables against fuel price shocks.
- These numbers describe what happened together; they do not prove cause and effect on their own (see *Method and limitations*).
""",
    },
    "when": {
        "read": "Rows are hours of the day, columns are months. The darker the cell, the more hours with a "
                "negative price at that time. Use the year slider above to compare periods.",
        "judge": """
- **Midday, spring and summer:** negative prices are driven by solar power, which peaks at the same time everywhere.
- **For whom is it good?** Consumers with a dynamic tariff, batteries, electric cars and industry that can shift demand can buy very cheap power.
- **For whom is it bad?** Producers earn nothing or pay. Older renewable plants with fixed support still get paid, which raises the cost of the subsidy account; newer plants increasingly get nothing during negative prices.
- **For the system:** it signals missing flexibility. The goal is not zero negative hours, but using that cheap power instead of curtailing it.
""",
    },
    "recent": {
        "read": "Top: the price for every quarter hour of the last 7 days. Bottom: how much wind and solar "
                "produced (stacked areas) compared with consumption (line). Where the areas reach the line, "
                "wind and solar alone could cover demand.",
        "judge": """
- **Price dips line up with solar peaks** at midday and with windy periods; price peaks appear in the evening when the sun is gone but demand is still high.
- **The gap between the areas and the line** is what other plants and imports have to fill (the residual load).
- **Quarter-hour prices** show short spikes and dips that an hourly average would smooth away. For batteries and flexible consumers these short moments are exactly where money is made or saved.
""",
    },
}
