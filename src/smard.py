"""Minimal client for the SMARD chart data API (see docs/api_notes.md).

Two calls: the index of available weekly chunks, and one chunk of data.
Transient errors are retried with backoff, and requests are spaced out a little
so a full backfill does not hammer the server.
"""
import time

import pandas as pd
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from src.series import REGION, RESOLUTION

BASE_URL = "https://www.smard.de/app/chart_data"
TIMEOUT = 30  # seconds
PAUSE = 0.1  # seconds between requests


def make_session() -> requests.Session:
    retry = Retry(
        total=5,
        backoff_factor=1,  # 1, 2, 4, 8, 16 seconds
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"],
    )
    session = requests.Session()
    session.mount("https://", HTTPAdapter(max_retries=retry))
    session.headers["User-Agent"] = "smard-energy-pipeline (portfolio project)"
    return session


def index_url(series_id: int, region: str = REGION, resolution: str = RESOLUTION) -> str:
    return f"{BASE_URL}/{series_id}/{region}/index_{resolution}.json"


def chunk_url(series_id: int, chunk_ts: int, region: str = REGION, resolution: str = RESOLUTION) -> str:
    # filter and region appear twice in the path and must match, otherwise 404
    return f"{BASE_URL}/{series_id}/{region}/{series_id}_{region}_{resolution}_{chunk_ts}.json"


def _get_json(session: requests.Session, url: str) -> dict:
    response = session.get(url, timeout=TIMEOUT)
    response.raise_for_status()
    time.sleep(PAUSE)
    return response.json()


def fetch_index(session: requests.Session, series_id: int) -> list[int]:
    """Start timestamps (epoch ms, UTC) of all available weekly chunks, oldest first."""
    return sorted(_get_json(session, index_url(series_id))["timestamps"])


def fetch_chunk(session: requests.Session, series_id: int, chunk_ts: int) -> list[list]:
    """Raw `[timestamp_ms, value]` pairs of one weekly chunk."""
    return _get_json(session, chunk_url(series_id, chunk_ts))["series"]


def chunk_to_frame(series_id: int, pairs: list[list]) -> pd.DataFrame:
    """Turn raw pairs into a tidy frame with columns series_id, ts_utc, value.

    Trailing nulls are slots that are not published yet (the current week is padded
    to its full length), so they are dropped. Nulls in the middle are real gaps and
    are kept, so the data-quality tests can find them.
    """
    frame = pd.DataFrame(pairs, columns=["ts_ms", "value"])
    published = frame["value"].notna()
    if published.any():
        last = published[published].index[-1]
        frame = frame.loc[:last]
    else:
        frame = frame.iloc[0:0]
    return pd.DataFrame(
        {
            "series_id": pd.Series(series_id, index=frame.index, dtype="int32"),
            "ts_utc": pd.to_datetime(frame["ts_ms"].astype("int64"), unit="ms", utc=True),
            "value": frame["value"].astype("float64"),
        }
    ).reset_index(drop=True)
