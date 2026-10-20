"""Raw layer: one Parquet file per series and UTC month.

    data/raw/series=4169/month=2026-10.parquet

Writes are upserts on (series_id, ts_utc): new rows replace existing rows with the
same timestamp, everything else in the file is kept. Loading the same data twice
therefore gives the same files (idempotent), and late corrections by SMARD simply
overwrite the old values.
"""
from pathlib import Path

import pandas as pd

RAW_DIR = Path("data/raw")
COLUMNS = ["series_id", "ts_utc", "value"]


def partition_path(root: Path, series_id: int, month: str) -> Path:
    return Path(root) / f"series={series_id}" / f"month={month}.parquet"


def read_partition(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame(
            {
                "series_id": pd.Series(dtype="int32"),
                "ts_utc": pd.Series(dtype="datetime64[ms, UTC]"),
                "value": pd.Series(dtype="float64"),
            }
        )
    return pd.read_parquet(path)[COLUMNS]


def upsert(frame: pd.DataFrame, root: Path = RAW_DIR) -> list[Path]:
    """Merge `frame` into the monthly partitions it touches. Returns the written paths."""
    if frame.empty:
        return []
    frame = frame.assign(ts_utc=frame["ts_utc"].astype("datetime64[ms, UTC]"))
    months = frame["ts_utc"].dt.strftime("%Y-%m")
    written = []
    for (series_id, month), new in frame.groupby([frame["series_id"], months]):
        path = partition_path(root, int(series_id), month)
        merged = (
            pd.concat([read_partition(path), new[COLUMNS]], ignore_index=True)
            .drop_duplicates(subset=["series_id", "ts_utc"], keep="last")
            .sort_values("ts_utc", ignore_index=True)
            .astype({"series_id": "int32", "value": "float64"})
        )
        path.parent.mkdir(parents=True, exist_ok=True)
        # write to a temp file first, so a crash never leaves a half-written partition
        tmp = path.with_suffix(".parquet.tmp")
        merged.to_parquet(tmp, index=False)
        tmp.replace(path)
        written.append(path)
    return written


def latest_timestamp(series_id: int, root: Path = RAW_DIR) -> pd.Timestamp | None:
    """Newest stored timestamp of a series, or None if nothing is stored yet."""
    files = sorted((Path(root) / f"series={series_id}").glob("month=*.parquet"))
    if not files:
        return None
    stored = read_partition(files[-1])
    return stored["ts_utc"].max() if not stored.empty else None
