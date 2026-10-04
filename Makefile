PYTHON := .venv/bin/python
PROFILE_SCRIPT := scripts/profile_dataset.py
DATA_SCRIPT := scripts/build_evs_parquet.py
PROFILE_REPORT := reports/data_profile_evs.md
PARQUET_DATA := data/processed/evs_v5_0.parquet
REQUIREMENTS_STAMP := .venv/.requirements-installed

.DEFAULT_GOAL := profile

.PHONY: profile profile-all report data setup test check help

profile: $(PYTHON)
	@$(PYTHON) $(PROFILE_SCRIPT) --study EVS

profile-all: $(PYTHON)
	@$(PYTHON) $(PROFILE_SCRIPT) --study all

report: $(PYTHON)
	@$(PYTHON) $(PROFILE_SCRIPT) --study EVS --output $(PROFILE_REPORT)

data: $(REQUIREMENTS_STAMP)
	@$(PYTHON) $(DATA_SCRIPT) --output $(PARQUET_DATA)

setup: $(REQUIREMENTS_STAMP)
	@echo "Virtual environment ready: $(PYTHON)"

test: $(REQUIREMENTS_STAMP)
	@PYTHONPATH=src $(PYTHON) -m unittest discover -s tests -p 'test_*.py'

check: $(REQUIREMENTS_STAMP)
	@$(PYTHON) -m compileall -q scripts src tests
	@PYTHONPATH=src $(PYTHON) -m unittest discover -s tests -p 'test_*.py'
	@echo "Profiler checks passed."

help:
	@echo "Available commands:"
	@echo "  make          Print the EVS-focused dataset profile"
	@echo "  make profile  Print the EVS-focused dataset profile"
	@echo "  make profile-all  Print the complete joint EVS/WVS profile"
	@echo "  make report   Print and save the EVS profile to $(PROFILE_REPORT)"
	@echo "  make data     Build and validate $(PARQUET_DATA)"
	@echo "  make setup    Create the environment and install requirements"
	@echo "  make test     Run unit tests"
	@echo "  make check    Compile modules and run unit tests"

$(PYTHON):
	python3 -m venv .venv

$(REQUIREMENTS_STAMP): requirements.txt | $(PYTHON)
	$(PYTHON) -m pip install -r requirements.txt
	@touch $(REQUIREMENTS_STAMP)
