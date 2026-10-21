# One-command workflow. Run `make help` to see the targets.
PYTHON ?= python3
DBT ?= dbt

.PHONY: help install test backfill update transform export pipeline pull-data dashboard clean

help:
	@echo "make install   install Python packages"
	@echo "make test      run the unit tests (no network needed)"
	@echo "make backfill  load the full history from SMARD into data/raw (takes ~25 min)"
	@echo "make update    re-load the last two weeks (first part of the daily job)"
	@echo "make transform build the DuckDB models with dbt and run the data tests"
	@echo "make export    write the marts as Parquet to data/marts (for the dashboard)"
	@echo "make pipeline  update + transform + export (what the daily job runs)"
	@echo "make pull-data download the published data from the data branch (instead of a backfill)"
	@echo "make dashboard start the Streamlit dashboard on http://localhost:8501"
	@echo "make clean     remove the local database and caches"

install:
	$(PYTHON) -m pip install -r requirements.txt

test:
	$(PYTHON) -m pytest

backfill:
	$(PYTHON) -m src.ingest backfill

update:
	$(PYTHON) -m src.ingest update

transform:
	cd transform && $(DBT) build --profiles-dir .

export:
	$(PYTHON) -m src.export

pipeline: update transform export

pull-data:
	scripts/data_branch.sh pull

dashboard:
	$(PYTHON) -m streamlit run dashboard/app.py

clean:
	rm -f data/processed/*.duckdb data/processed/*.duckdb.wal
	rm -rf .pytest_cache transform/target transform/logs
