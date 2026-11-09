#!/usr/bin/env python3
"""Product parity and data-free installed-command checks on synthetic profiles."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

from evs_model.cli import load_bundle, predict_frame
from evs_model.config import CORE
from evs_model.training import file_hash, write_json

ROOT = Path(__file__).resolve().parents[1]


def main():
    bundle = load_bundle(ROOT / "models/evs_v0_1_0.joblib")
    metadata = json.loads((ROOT / "models/evs_v0_1_0.metadata.json").read_text())
    assert file_hash(ROOT / "models/evs_v0_1_0.joblib") == metadata["artifact_sha256"]
    rng = np.random.default_rng(42)
    n = 120
    sample = pd.DataFrame({"X001": rng.integers(1, 3, n), "X003": rng.integers(18, 83, n),
        "X025R": rng.integers(1, 4, n), "X028": rng.integers(1, 9, n),
        "X047E_EVS5": rng.integers(1, 11, n), "A009": rng.integers(1, 6, n),
        "A165": rng.integers(1, 3, n), "A173": rng.integers(1, 11, n),
        "cntry_AN": rng.choice(bundle["countries"], n)})
    sample.loc[:4, "X047E_EVS5"] = [-1, -2, -3, -4, -5]
    sample.loc[5, "X003"] = np.nan
    expected = predict_frame(bundle, sample)
    local = joblib.load(ROOT / "02_develop/local" / f"{bundle['model_name']}.joblib")
    from evs_model.data import clean_features
    p_original = local.predict_proba(clean_features(sample))
    np.testing.assert_allclose(expected[[f"p_{i}" for i in range(1, 11)]], p_original, atol=1e-12)
    with tempfile.TemporaryDirectory() as d:
        source, output = Path(d) / "profiles.csv", Path(d) / "predictions.csv"
        sample.to_csv(source, index=False)
        completed = subprocess.run([str(Path(sys.executable).parent / "evs-predict"),
            "--model", str(ROOT / "models/evs_v0_1_0.joblib"), "--input", str(source), "--output", str(output)], check=True, capture_output=True, text=True)
        actual = pd.read_csv(output)
    difference = float(np.max(np.abs(actual.to_numpy() - expected.to_numpy())))
    assert difference < 1e-6
    suite = unittest.defaultTestLoader.discover(str(ROOT / "tests"), pattern="test_*.py")
    result = unittest.TextTestRunner(verbosity=1).run(suite)
    if not result.wasSuccessful():
        raise SystemExit(1)
    clean_python = ROOT / ".venv-verify/bin/python"
    clean_checked = False
    if clean_python.is_file():
        command = [str(clean_python.parent / "evs-predict"), "--model", str(ROOT / "models/evs_v0_1_0.joblib"),
                   "--input", str(ROOT / "examples/respondents.csv")]
        with tempfile.TemporaryDirectory() as d:
            output = Path(d) / "clean.csv"
            subprocess.run([*command, "--output", str(output)], check=True, capture_output=True, text=True)
            clean_result = pd.read_csv(output)
            expected_example = predict_frame(bundle, pd.read_csv(ROOT / "examples/respondents.csv"))
            np.testing.assert_allclose(clean_result, expected_example, atol=1e-12)
            location = subprocess.check_output([str(clean_python), "-c", "import evs_model; print(evs_model.__file__)"], text=True).strip()
            assert ".venv-verify" in location and "/site-packages/" in location
        clean_checked = True
    notebook = json.loads((ROOT / "notebooks/quickstart.ipynb").read_text())
    code_cells = [c for c in notebook["cells"] if c["cell_type"] == "code"]
    notebook_executed = all(c.get("execution_count") is not None and
                            not any(o.get("output_type") == "error" for o in c.get("outputs", [])) for c in code_cells)
    path = ROOT / "02_develop/results/production_checks.json"
    previous = json.loads(path.read_text()) if path.exists() else {}
    write_json(path, {
        "unit_tests": result.testsRun, "synthetic_cases": n, "max_probability_difference": difference,
        "saved_model_matches_training_estimator": True, "clean_environment_installation": clean_checked,
        "model_sha256": metadata["artifact_sha256"], "notebook_executed": notebook_executed,
        "hosted_ci_status": previous.get("hosted_ci_status", "workflow prepared; server status not yet verified"),
        "cli_output": f"Predicted {len(actual)} synthetic respondents successfully."})
    print(json.dumps({"tests": result.testsRun, "synthetic_cases": n, "max_difference": difference}))


if __name__ == "__main__":
    main()
