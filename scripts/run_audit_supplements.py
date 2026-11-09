#!/usr/bin/env python3
"""Reproduce supplementary loss/seed diagnostics without touching test data."""

from pathlib import Path
from evs_model.audit_analysis import run_audit_supplements

ROOT = Path(__file__).resolve().parents[1]
run_audit_supplements(ROOT / "data/processed/evs_v5_0.parquet", ROOT)
