PYTHON ?= .venv/bin/python
PYTHON_BASE ?= python3.12
PROFILE_SCRIPT := scripts/profile_dataset.py
DATA_SCRIPT := scripts/build_evs_parquet.py
PROFILE_REPORT := 01_define/report/data_profile_evs.md
PARQUET_DATA := data/processed/evs_v5_0.parquet
REQUIREMENTS_STAMP := $(dir $(PYTHON)).project-installed

.DEFAULT_GOAL := profile

.PHONY: profile profile-all report data setup test check help train inference develop-reports predict-example verify-production package

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
	@echo "Project checks passed."

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
	@echo "  make train    Tune models using training-only validation"
	@echo "  make inference  Weighted descriptions and approximate intervals"
	@echo "  make develop-reports  Render the three Develop PDF reports"
	@echo "  make predict-example  Predict synthetic example profiles"
	@echo "  make verify-production  Saved-model and installed-command checks"
	@echo "  make package  Build wheel and source distribution"

$(PYTHON):
	$(PYTHON_BASE) -m venv $(patsubst %/bin/python,%,$(PYTHON))

$(REQUIREMENTS_STAMP): pyproject.toml requirements-lock.txt | $(PYTHON)
	$(PYTHON) -m pip install -r requirements-lock.txt
	$(PYTHON) -m pip install --no-build-isolation --no-deps -e .
	@touch $(REQUIREMENTS_STAMP)

train: $(REQUIREMENTS_STAMP)
	@OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 $(PYTHON) -c 'from evs_model.cli import train_main; train_main()'

inference: $(REQUIREMENTS_STAMP)
	@OPENBLAS_NUM_THREADS=1 $(PYTHON) -c 'from evs_model.cli import infer_main; infer_main()'

develop-reports: $(REQUIREMENTS_STAMP)
	@MPLCONFIGDIR=.cache/matplotlib $(PYTHON) scripts/build_develop_reports.py

predict-example: $(REQUIREMENTS_STAMP)
	@$(dir $(PYTHON))evs-predict --input examples/respondents.csv --output examples/predictions.csv

verify-production: $(REQUIREMENTS_STAMP)
	@OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 $(PYTHON) scripts/verify_production.py

package: $(REQUIREMENTS_STAMP)
	@$(PYTHON) -m build --no-isolation
