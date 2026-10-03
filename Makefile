PYTHON := .venv/bin/python
PROFILE_SCRIPT := scripts/profile_dataset.py
PROFILE_REPORT := reports/data_profile.md

.DEFAULT_GOAL := profile

.PHONY: profile report setup check help

profile: $(PYTHON)
	@$(PYTHON) $(PROFILE_SCRIPT)

report: $(PYTHON)
	@$(PYTHON) $(PROFILE_SCRIPT) --output $(PROFILE_REPORT)

setup: $(PYTHON)
	@echo "Virtual environment ready: $(PYTHON)"

check: $(PYTHON)
	@$(PYTHON) -m py_compile $(PROFILE_SCRIPT)
	@echo "Profiler syntax check passed."

help:
	@echo "Available commands:"
	@echo "  make          Print the complete dataset profile"
	@echo "  make profile  Print the complete dataset profile"
	@echo "  make report   Print and save it to $(PROFILE_REPORT)"
	@echo "  make setup    Create the local virtual environment"
	@echo "  make check    Validate the Python profiler"

$(PYTHON):
	python3 -m venv .venv
