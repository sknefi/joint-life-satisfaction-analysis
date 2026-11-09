"""Substantive safeguards for ordinal fitting, split isolation and prediction."""

import tempfile
import unittest
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from scipy.optimize import check_grad

from evs_model.cli import predict_frame, predict_main
from evs_model.config import CORE
from evs_model.data import clean_features, split_respondents, within_country_folds
from evs_model.inference import weighted_summary
from evs_model.metrics import scores
from evs_model.models import OrdinalLogit, SurveyEncoder, make_model, median_predictions


def synthetic_frame(n=400, countries=("CZ", "SK", "AT", "DE", "FR", "PL", "ES", "IT")):
    rng = np.random.default_rng(42)
    return pd.DataFrame({"uniqid": np.arange(n), "cntry_AN": np.resize(countries, n),
        "A170": np.resize(np.arange(1, 11), n), "X001": rng.integers(1, 3, n),
        "X003": rng.integers(18, 83, n), "X025R": rng.integers(1, 4, n),
        "X028": rng.integers(1, 9, n), "X047E_EVS5": rng.integers(1, 11, n),
        "A009": rng.integers(1, 6, n), "A165": rng.integers(1, 3, n),
        "A173": rng.integers(1, 11, n), "A008": rng.integers(1, 5, n)})


class ModellingTests(unittest.TestCase):
    def test_split_reproducible_and_country_isolated(self):
        frame = synthetic_frame(1600)
        labels, countries = split_respondents(frame, holdout_count=2)
        again, again_countries = split_respondents(frame, holdout_count=2)
        pd.testing.assert_series_equal(labels, again)
        self.assertEqual(countries, again_countries)
        self.assertFalse(set(frame.loc[labels.eq("train"), "cntry_AN"]) & set(countries))
        self.assertTrue(labels.loc[frame.cntry_AN.isin(countries)].eq("country_test").all())
        training = frame.loc[labels.eq("train")]
        seen = []
        for a, b in within_country_folds(training):
            self.assertFalse(set(a) & set(b))
            seen.extend(b)
        self.assertEqual(sorted(seen), list(range(len(training))))

    def test_validation_does_not_change_encoder_statistics(self):
        frame = clean_features(synthetic_frame())
        frame.loc[:9, "X003"] = np.nan
        encoder = SurveyEncoder().fit(frame.iloc[:200])
        median = encoder.age_median_
        validation = frame.iloc[200:].copy()
        validation["X003"] = 82
        validation["cntry_AN"] = "ZZ"
        encoded = encoder.transform(validation)
        self.assertEqual(encoder.age_median_, median)
        self.assertTrue(np.isfinite(encoded).all())

    def test_objective_gradient_matches_finite_differences(self):
        rng = np.random.default_rng(3)
        X = rng.normal(size=(50, 4))
        y = np.resize(np.arange(10), 50)
        parameters = np.r_[rng.normal(size=4), -2, np.full(8, .5)]
        error = check_grad(lambda p: OrdinalLogit.objective(p, X, y, 1.)[0],
                           lambda p: OrdinalLogit.objective(p, X, y, 1.)[1], parameters)
        self.assertLess(error, 1e-4)

    def test_ordinal_intercept_distribution_and_roundtrip(self):
        # With no signal and balanced outcomes the threshold optimum gives 0.1
        # per category; this checks signs, boundaries and class ordering.
        model = OrdinalLogit().fit(np.zeros((200, 1)), np.resize(np.arange(1, 11), 200))
        p = model.predict_proba(np.zeros((10, 1)))
        np.testing.assert_allclose(p, .1, atol=1e-5)
        self.assertTrue(model.optimization_["success"])
        self.assertTrue(np.all(np.diff(model.theta_) >= 0))

    def test_missing_codes_invalid_and_target_leakage(self):
        frame = synthetic_frame().loc[:, list(CORE)].head(5)
        for i in range(5):
            frame.loc[i, "X047E_EVS5"] = -i - 1
        clean = clean_features(frame, countries=frame.cntry_AN.unique(), strict=True)
        self.assertTrue(clean.X047E_EVS5.isna().all())
        for field, bad in (("X003", 83), ("X001", 1.5), ("A173", 11), ("A165", float("inf"))):
            invalid = frame.copy()
            invalid[field] = bad
            with self.assertRaises(ValueError):
                clean_features(invalid, strict=True)
        with self.assertRaises(ValueError):
            clean_features(frame.assign(A170=7), strict=True)
        with self.assertRaises(ValueError):
            clean_features(frame.assign(cntry_AN="ZZ"), countries=["SK"], strict=True)

    def test_probability_metrics_and_median(self):
        p = np.zeros((2, 10)); p[0, 0] = 1; p[1, 9] = 1
        self.assertEqual(scores([1, 10], p)["mae"], 0)
        self.assertEqual(scores([1, 10], p)["rps"], 0)
        np.testing.assert_array_equal(median_predictions(p), [1, 10])
        with self.assertRaises(ValueError):
            scores([1, 10], p * 2)

    def test_saved_model_and_cli_match_in_memory(self):
        raw = synthetic_frame()
        X = clean_features(raw)
        model = make_model("ordinal", {"alpha": 10}).fit(X, raw.A170)
        bundle = {"schema_version": 1, "classes": list(range(1, 11)), "features": list(CORE),
                  "countries": sorted(raw.cntry_AN.unique()), "estimator": model}
        sample = raw.loc[:19, list(CORE)]
        expected = predict_frame(bundle, sample)
        with tempfile.TemporaryDirectory() as d:
            model_path = Path(d) / "model.joblib"
            source, output = Path(d) / "input.csv", Path(d) / "output.csv"
            joblib.dump(bundle, model_path)
            sample.to_csv(source, index=False)
            self.assertEqual(predict_main(["--model", str(model_path), "--input", str(source), "--output", str(output)]), 0)
            actual = pd.read_csv(output)
            np.testing.assert_allclose(actual, expected, atol=1e-12)
            before = output.read_bytes()
            sample.assign(A170=7).to_csv(source, index=False)
            self.assertEqual(predict_main(["--model", str(model_path), "--input", str(source), "--output", str(output)]), 2)
            self.assertEqual(output.read_bytes(), before)

    def test_survey_weight_estimate_and_effective_size(self):
        result = weighted_summary([0, 1], [1, 3])
        self.assertEqual(result["estimate"], .75)
        self.assertAlmostEqual(result["effective_n"], 1.6)


if __name__ == "__main__":
    unittest.main()
