"""Load SMARD series into the raw Parquet layer.

    python -m src.ingest backfill            # full history since HISTORY_START
    python -m src.ingest update              # only recent weeks (daily job)
    python -m src.ingest update --series 4169 4068

`update` re-loads everything from two weeks before the newest stored value. That
picks up SMARD's late corrections and also closes gaps if the daily job missed a
few runs. A series with no stored data yet falls back to a full backfill.
"""
import argparse
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd

from src import smard, storage
from src.series import HISTORY_START, SERIES

log = logging.getLogger("ingest")

RELOAD_WINDOW = timedelta(weeks=2)


def to_ms(moment: datetime) -> int:
    return int(moment.timestamp() * 1000)


def select_chunks(index: list[int], mode: str, latest: pd.Timestamp | None) -> list[int]:
    """Pick the weekly chunks to (re-)load from the index."""
    if mode == "update" and latest is not None:
        # also include the chunk that contains (latest - window)
        cutoff = to_ms(latest.to_pydatetime() - RELOAD_WINDOW)
        earlier = [ts for ts in index if ts <= cutoff]
        start = earlier[-1] if earlier else index[0]
    else:
        start = to_ms(HISTORY_START)
    return [ts for ts in index if ts >= start]


def load_series(session, series_id: int, mode: str, root: Path) -> int:
    """Load one series. Returns the number of rows written."""
    index = smard.fetch_index(session, series_id)
    latest = storage.latest_timestamp(series_id, root)
    chunks = select_chunks(index, mode, latest)
    frames = [smard.chunk_to_frame(series_id, smard.fetch_chunk(session, series_id, ts)) for ts in chunks]
    frame = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
    storage.upsert(frame, root)
    return len(frame)


def run(mode: str, series_ids: list[int], root: Path = storage.RAW_DIR) -> dict[int, int]:
    session = smard.make_session()
    failed, rows = [], {}
    for series_id in series_ids:
        name = SERIES[series_id][0]
        try:
            rows[series_id] = load_series(session, series_id, mode, root)
            log.info("%-24s %5d  %8d rows", name, series_id, rows[series_id])
        except Exception:
            # one broken series should not stop the others; the run still fails below
            log.exception("%-24s %5d  FAILED", name, series_id)
            failed.append(series_id)
    if failed:
        raise SystemExit(f"{len(failed)} series failed: {failed}")
    return rows


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("mode", choices=["backfill", "update"])
    parser.add_argument("--series", type=int, nargs="+", choices=sorted(SERIES), default=list(SERIES))
    parser.add_argument("--root", type=Path, default=storage.RAW_DIR)
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    started = datetime.now(timezone.utc)
    run(args.mode, args.series, args.root)
    log.info("done in %s", datetime.now(timezone.utc) - started)


if __name__ == "__main__":
    main()
