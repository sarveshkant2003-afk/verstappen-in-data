PY := .venv/bin/python
SITE ?=

.PHONY: setup data laps audit test charts site refresh all

setup:            ## create the venv and install pinned dependencies
	python3.12 -m venv .venv
	$(PY) -m pip install -r requirements.txt

data:             ## fetch (cached) Jolpica data and build data/processed/*.parquet
	$(PY) -m src.download
	$(PY) -m src.results

audit: data       ## re-run the coverage audit notebook
	.venv/bin/jupyter nbconvert --to notebook --execute --inplace notebooks/01_data_audit.ipynb

test:             ## stat-rule unit tests
	$(PY) -m pytest -q

laps:             ## FastF1 race laps 2018+ (resumable; only missing races are fetched)
	$(PY) -m src.laps

charts:           ## facts.json, every chart (web JSON + PNG), the poster and README.md
	$(PY) -m src.features
	$(PY) -m src.build_charts
	$(PY) -m src.poster
	$(PY) scripts/build_readme.py

site:             ## copy chart JSON/PNG into the website repo: make site SITE=<path>
	@test -n "$(SITE)" || (echo "usage: make site SITE=<path to website repo>"; exit 1)
	$(PY) scripts/export_to_site.py $(SITE)

refresh:          ## after a new race: re-fetch the live season, its laps, rebuild everything
	$(PY) -m src.download --refresh
	$(PY) -m src.results
	$(PY) -m src.laps
	$(MAKE) test charts
	@if [ -n "$(SITE)" ]; then $(MAKE) site SITE=$(SITE); fi

all: data test charts
