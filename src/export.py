"""Export the dbt marts as Parquet files for the dashboard.

    python -m src.export

The dashboard reads these small files (data/marts/*.parquet) instead of the DuckDB
database, so it needs neither dbt nor the 100 MB database file.
"""
import logging
from pathlib import Path

import duckdb

DATABASE = Path("data/processed/smard.duckdb")
MARTS_DIR = Path("data/marts")
MARTS = ["fct_quarter_hours", "fct_hours", "fct_days"]

log = logging.getLogger("export")


def export(database: Path = DATABASE, out_dir: Path = MARTS_DIR) -> list[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    written = []
    with duckdb.connect(str(database), read_only=True) as con:
        for name in MARTS:
            path = out_dir / f"{name}.parquet"
            con.execute(f"copy (select * from {name} order by 1) to '{path}' (format parquet, compression zstd)")
            rows = con.execute(f"select count(*) from {name}").fetchone()[0]
            log.info("%-18s %8d rows -> %s", name, rows, path)
            written.append(path)
    return written


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    export()
