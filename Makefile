PY := .venv/bin/python
SITE ?=

.PHONY: setup data audit test charts site refresh all

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

charts:           ## render every chart to output/web (JSON) and output/static (PNG)
	$(PY) -m src.build_charts

site:             ## copy chart JSON/PNG into the website repo: make site SITE=<path>
	@test -n "$(SITE)" || (echo "usage: make site SITE=<path to website repo>"; exit 1)
	$(PY) scripts/export_to_site.py $(SITE)

refresh:          ## after a new 2026 race: re-fetch the live season, rebuild tables and charts
	$(PY) -m src.download --refresh
	$(PY) -m src.results
	$(MAKE) test charts
	@if [ -n "$(SITE)" ]; then $(MAKE) site SITE=$(SITE); fi

all: data test charts
