# One-command workflow. Run `make help` to see the targets.
PYTHON ?= python3

.PHONY: help install test backfill update clean

help:
	@echo "make install   install Python packages"
	@echo "make test      run the unit tests (no network needed)"
	@echo "make backfill  load the full history from SMARD into data/raw (takes ~25 min)"
	@echo "make update    re-load the last two weeks (what the daily job runs)"
	@echo "make clean     remove the local database and caches"

install:
	$(PYTHON) -m pip install -r requirements.txt

test:
	$(PYTHON) -m pytest

backfill:
	$(PYTHON) -m src.ingest backfill

update:
	$(PYTHON) -m src.ingest update

clean:
	rm -f data/processed/*.duckdb data/processed/*.duckdb.wal
	rm -rf .pytest_cache
