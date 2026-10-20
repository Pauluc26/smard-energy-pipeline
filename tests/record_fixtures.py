"""Record real SMARD responses as test fixtures, so the unit tests run without network.

    python -m tests.record_fixtures

Only needs to be re-run if the API format changes. The "current week" fixture is a
snapshot of whatever week was current when it was recorded.
"""
import json
from datetime import datetime, timezone
from pathlib import Path

from src import smard

FIXTURES = Path(__file__).parent / "fixtures"
PRICE = 4169

# chunk start (Monday 00:00 German time, in UTC) -> fixture name
WEEKS = {
    datetime(2026, 10, 11, 22, tzinfo=timezone.utc): "week_normal",
    datetime(2025, 10, 19, 22, tzinfo=timezone.utc): "week_dst_autumn",  # 26 Oct 2025 has 25 hours
    datetime(2026, 3, 22, 23, tzinfo=timezone.utc): "week_dst_spring",  # 29 Mar 2026 has 23 hours
}


def main() -> None:
    FIXTURES.mkdir(exist_ok=True)
    session = smard.make_session()
    index = smard.fetch_index(session, PRICE)
    (FIXTURES / "index_4169.json").write_text(json.dumps({"timestamps": index}))
    chunks = {int(start.timestamp() * 1000): name for start, name in WEEKS.items()}
    chunks[index[-1]] = "week_current"
    for ts, name in chunks.items():
        series = smard.fetch_chunk(session, PRICE, ts)
        (FIXTURES / f"{name}_4169.json").write_text(json.dumps({"chunk_ts": ts, "series": series}))
        print(f"{name:16s} {len(series)} slots")


if __name__ == "__main__":
    main()
