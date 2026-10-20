"""The SMARD series this pipeline loads. Filter IDs are verified in docs/api_notes.md.

The list itself lives in transform/seeds/series.csv, so ingestion (Python) and the
data-quality tests (dbt) share one source of truth.
"""
import csv
from datetime import datetime, timezone
from pathlib import Path

REGION = "DE"
RESOLUTION = "quarterhour"

# First weekly chunk to load: the week of 1 October 2018, when the DE-LU bidding zone
# started. Chunks begin Monday 00:00 German time, which is Sunday 22:00 UTC in summer.
HISTORY_START = datetime(2018, 9, 30, 22, 0, tzinfo=timezone.utc)

SEED = Path(__file__).resolve().parent.parent / "transform" / "seeds" / "series.csv"

with SEED.open() as f:
    # filter id -> (name, category)
    SERIES: dict[int, tuple[str, str]] = {
        int(row["series_id"]): (row["name"], row["category"]) for row in csv.DictReader(f)
    }
