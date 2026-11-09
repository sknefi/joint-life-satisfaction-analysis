"""Audit safeguards: genuine loss change and training-only inference."""

import unittest
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.optimize import check_grad

from evs_model.audit_analysis import huber_objective, training_inference_frame
from evs_model.cli import load_bundle, predict_frame
from evs_model.data import split_respondents
from test_modelling import synthetic_frame


class AuditTests(unittest.TestCase):
    def test_huber_gradient_and_robust_tail(self):
        rng = np.random.default_rng(7)
        X = rng.normal(size=(80, 5)); y = rng.normal(size=80); coef = rng.normal(size=5)
        error = check_grad(lambda b: huber_objective(b, X, y)[0],
                           lambda b: huber_objective(b, X, y)[1], coef)
        self.assertLess(error, 1e-6)
        value, gradient = huber_objective(np.zeros(1), np.ones((1, 1)), np.array([100.]))
        self.assertEqual(value, 99.5)
        self.assertEqual(gradient[0], -1.)

    def test_inference_uses_only_training_cases_and_corrects_split_design(self):
        raw = synthetic_frame(1600).assign(gwght=1., wght_eq1000=1., pwght=1.)
        frame, held = training_inference_frame(raw)
        labels, _ = split_respondents(raw)
        self.assertEqual(set(frame.uniqid), set(raw.loc[labels.eq('train'), 'uniqid']))
        self.assertFalse(set(frame.cntry_AN) & set(held))
        self.assertTrue(frame.split_probability.between(0, 1).all())
        np.testing.assert_allclose(frame.analysis_weight, 1 / frame.split_probability)

    def test_holdout_predictors_and_weights_cannot_change_inference(self):
        raw = synthetic_frame(1600).assign(gwght=1., wght_eq1000=1., pwght=1.)
        before, _ = training_inference_frame(raw)
        labels, _ = split_respondents(raw)
        raw.loc[~labels.eq('train'), ['gwght', 'X047E_EVS5', 'X028']] = 999999
        after, _ = training_inference_frame(raw)
        pd.testing.assert_frame_equal(before, after)

    def test_saved_part_two_synthetic_predictions_match_release(self):
        root = Path(__file__).resolve().parents[1]
        if not (root / 'models/evs_v0_1_0.joblib').exists():
            self.skipTest('The code-only distribution does not bundle the separately distributed model.')
        bundle = load_bundle(root / 'models/evs_v0_1_0.joblib')
        profiles = pd.read_csv(root / 'examples/reference_profiles.csv')
        expected = pd.read_csv(root / 'examples/reference_predictions.csv')
        np.testing.assert_allclose(predict_frame(bundle, profiles), expected, atol=1e-12, rtol=0)


if __name__ == '__main__':
    unittest.main()
