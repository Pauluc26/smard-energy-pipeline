"""Unit tests for the ingestion code. They use recorded API responses (tests/fixtures),
so no network is needed."""
import json
from pathlib import Path

import pandas as pd
import pytest

from src import ingest, smard, storage
from src.series import HISTORY_START

FIXTURES = Path(__file__).parent / "fixtures"
QUARTER_HOUR = pd.Timedelta(minutes=15)


def load_fixture(name: str) -> dict:
    return json.loads((FIXTURES / f"{name}.json").read_text())


def frame_from(name: str) -> pd.DataFrame:
    return smard.chunk_to_frame(4169, load_fixture(name)["series"])


# --- chunk_to_frame ---------------------------------------------------------------

@pytest.mark.parametrize(
    "name, slots",
    [("week_normal_4169", 672), ("week_dst_autumn_4169", 676), ("week_dst_spring_4169", 668)],
)
def test_full_week_has_expected_quarter_hours(name, slots):
    frame = frame_from(name)
    assert len(frame) == slots
    assert frame["value"].notna().all()


@pytest.mark.parametrize("name", ["week_normal_4169", "week_dst_autumn_4169", "week_dst_spring_4169"])
def test_time_axis_is_continuous_in_utc(name):
    # in UTC there is no clock change: always exactly 15 minutes between rows
    ts = frame_from(name)["ts_utc"]
    assert str(ts.dt.tz) == "UTC"
    assert (ts.diff().dropna() == QUARTER_HOUR).all()


def test_week_starts_monday_midnight_german_time():
    for name in ["week_normal_4169", "week_dst_autumn_4169", "week_dst_spring_4169"]:
        first = frame_from(name)["ts_utc"].iloc[0].tz_convert("Europe/Berlin")
        assert (first.weekday(), first.hour, first.minute) == (0, 0, 0)


def test_current_week_drops_unpublished_slots():
    raw = load_fixture("week_current_4169")["series"]
    frame = smard.chunk_to_frame(4169, raw)
    assert 0 < len(frame) < len(raw)
    assert frame["value"].notna().all()


def test_trailing_nulls_dropped_but_gaps_kept():
    pairs = [[0, 1.0], [900_000, None], [1_800_000, 3.0], [2_700_000, None], [3_600_000, None]]
    frame = smard.chunk_to_frame(1, pairs)
    assert len(frame) == 3
    assert frame["value"].isna().tolist() == [False, True, False]


def test_all_null_chunk_gives_empty_frame():
    assert smard.chunk_to_frame(1, [[0, None], [900_000, None]]).empty


def test_chunk_url_repeats_filter_and_region():
    assert smard.chunk_url(4169, 123).endswith("/4169/DE/4169_DE_quarterhour_123.json")


# --- storage ----------------------------------------------------------------------

def test_upsert_is_idempotent(tmp_path):
    frame = frame_from("week_normal_4169")
    storage.upsert(frame, tmp_path)
    first = {p: p.read_bytes() for p in tmp_path.rglob("*.parquet")}
    storage.upsert(frame, tmp_path)
    second = {p: p.read_bytes() for p in tmp_path.rglob("*.parquet")}
    assert first == second


def test_upsert_replaces_corrected_values_and_keeps_the_rest(tmp_path):
    frame = frame_from("week_normal_4169")
    storage.upsert(frame, tmp_path)
    correction = frame.iloc[:4].assign(value=-1.0)
    storage.upsert(correction, tmp_path)
    stored = pd.concat(storage.read_partition(p) for p in sorted(tmp_path.rglob("*.parquet")))
    assert len(stored) == len(frame)
    assert (stored["value"].iloc[:4] == -1.0).all()
    assert stored["value"].iloc[4:].tolist() == frame["value"].iloc[4:].tolist()


def test_week_spanning_two_months_is_split(tmp_path):
    frame = frame_from("week_dst_autumn_4169")  # 20 Oct to 26 Oct 2025, one month
    shifted = frame.assign(ts_utc=frame["ts_utc"] + pd.Timedelta(days=10))  # 30 Oct to 5 Nov
    paths = storage.upsert(shifted, tmp_path)
    assert sorted(p.stem for p in paths) == ["month=2025-10", "month=2025-11"]
    total = sum(len(storage.read_partition(p)) for p in paths)
    assert total == len(shifted)


def test_latest_timestamp(tmp_path):
    assert storage.latest_timestamp(4169, tmp_path) is None
    frame = frame_from("week_normal_4169")
    storage.upsert(frame, tmp_path)
    assert storage.latest_timestamp(4169, tmp_path) == frame["ts_utc"].max()


# --- chunk selection and full run -------------------------------------------------

def test_backfill_starts_at_history_start():
    index = load_fixture("index_4169")["timestamps"]
    chunks = ingest.select_chunks(index, "backfill", latest=None)
    assert chunks[0] == ingest.to_ms(HISTORY_START)
    assert chunks[-1] == index[-1]


def test_update_without_data_falls_back_to_backfill():
    index = load_fixture("index_4169")["timestamps"]
    assert ingest.select_chunks(index, "update", None) == ingest.select_chunks(index, "backfill", None)


def test_update_reloads_two_weeks_before_latest():
    index = load_fixture("index_4169")["timestamps"]
    latest = pd.Timestamp(index[-1], unit="ms", tz="UTC") + pd.Timedelta(days=2)
    chunks = ingest.select_chunks(index, "update", latest)
    # the chunk containing (latest - 14 days) plus the two newer ones
    assert chunks == index[-3:]


def test_update_closes_gaps_after_missed_runs():
    index = load_fixture("index_4169")["timestamps"]
    latest = pd.Timestamp(index[-10], unit="ms", tz="UTC")  # job was down for ~9 weeks
    assert len(ingest.select_chunks(index, "update", latest)) == 12


def test_run_end_to_end_with_fake_api(tmp_path, monkeypatch):
    weeks = {load_fixture(n)["chunk_ts"]: load_fixture(n)["series"]
             for n in ["week_dst_autumn_4169", "week_normal_4169", "week_current_4169"]}
    # one more week right before the normal week, so the recent weeks have no gap
    normal = load_fixture("week_normal_4169")
    week_ms = 7 * 24 * 3600 * 1000
    weeks[normal["chunk_ts"] - week_ms] = [[ts - week_ms, v] for ts, v in normal["series"]]
    monkeypatch.setattr(smard, "fetch_index", lambda session, sid: sorted(weeks))
    monkeypatch.setattr(smard, "fetch_chunk", lambda session, sid, ts: weeks[ts])
    rows = ingest.run("backfill", [4169], tmp_path)
    again = ingest.run("update", [4169], tmp_path)
    stored = pd.concat(storage.read_partition(p) for p in tmp_path.rglob("*.parquet"))
    assert rows[4169] == len(stored)
    assert again[4169] == rows[4169] - 676  # update skips the old autumn week
    assert not stored.duplicated(["series_id", "ts_utc"]).any()


def test_run_reports_failed_series(tmp_path, monkeypatch):
    def broken(session, sid):
        raise ConnectionError("SMARD down")
    monkeypatch.setattr(smard, "fetch_index", broken)
    with pytest.raises(SystemExit, match="1 series failed"):
        ingest.run("update", [4169], tmp_path)
