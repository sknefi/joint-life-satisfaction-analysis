"""Predictive estimators and fold-local survey representation."""

from __future__ import annotations

import numpy as np
from scipy.optimize import minimize
from scipy.special import expit
from sklearn.base import BaseEstimator, ClassifierMixin, TransformerMixin
from sklearn.ensemble import HistGradientBoostingClassifier, RandomForestClassifier
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder

from .config import CORE, SEED


class SurveyEncoder(TransformerMixin, BaseEstimator):
    """Numeric age and age squared; explicit categories including missingness.

    Unknown categories become all-zero indicators for group-CV. Public prediction
    separately refuses countries not supported by the fitted release model.
    """

    def __init__(self, features=CORE):
        self.features = features

    def _categorical(self, X):
        columns = []
        for c in self.categorical_:
            values = X[c]
            if c == "cntry_AN":
                columns.append(values.fillna("__MISSING__").astype(str).to_numpy())
            else:
                columns.append(values.map(lambda v: "__MISSING__" if np.isnan(v) else str(int(v))).to_numpy())
        return np.column_stack(columns)

    def _numeric(self, X):
        age = X["X003"].to_numpy(dtype=float)
        missing = np.isnan(age)
        filled = np.where(missing, self.age_median_, age)
        return np.column_stack((filled, filled ** 2, missing.astype(float)))

    def fit(self, X, y=None):
        self.categorical_ = [c for c in self.features if c != "X003"]
        age = X["X003"].to_numpy(dtype=float)
        self.age_median_ = float(np.nanmedian(age)) if np.isfinite(age).any() else 50.
        numeric = self._numeric(X)
        self.mean_ = numeric.mean(axis=0)
        self.scale_ = numeric.std(axis=0)
        self.scale_[self.scale_ == 0] = 1.
        values = self._categorical(X)
        categories = [sorted(set(values[:, k]) | {"__MISSING__"}) for k in range(values.shape[1])]
        self.encoder_ = OneHotEncoder(categories=categories, handle_unknown="ignore", sparse_output=False)
        self.encoder_.fit(values)
        self.feature_names_ = ["age", "age_squared", "age_missing", *self.encoder_.get_feature_names_out(self.categorical_)]
        return self

    def transform(self, X):
        numeric = (self._numeric(X) - self.mean_) / self.scale_
        return np.column_stack((numeric, self.encoder_.transform(self._categorical(X))))


class EmpiricalBaseline(ClassifierMixin, BaseEstimator):
    def fit(self, X, y):
        self.classes_ = np.arange(1, 11)
        self.probabilities_ = np.bincount(np.asarray(y, dtype=int), minlength=11)[1:11] / len(y)
        return self

    def predict_proba(self, X):
        return np.tile(self.probabilities_, (len(X), 1))

    def predict(self, X):
        return median_predictions(self.predict_proba(X))


class OrdinalLogit(ClassifierMixin, BaseEstimator):
    """All-threshold logistic surrogate with L2 and ordered cutpoints.

    Objective follows the LogisticAT formulation (Rennie & Srebro, 2005),
    implemented here to retain OptimizeResult and projected-gradient diagnostics.
    This is not the exact ordered-logit categorical maximum likelihood.
    """

    def __init__(self, alpha=1., max_iter=2000, tol=1e-9):
        self.alpha, self.max_iter, self.tol = alpha, max_iter, tol

    @staticmethod
    def objective(parameters, X, y, alpha):
        p = X.shape[1]
        w, increments = parameters[:p], parameters[p:]
        theta = np.cumsum(increments)
        z = theta[:, None] - X.dot(w)[None, :]
        signs = np.where(np.arange(9)[:, None] >= y[None, :], 1., -1.)
        margin = signs * z
        loss = np.logaddexp(0, -margin).sum() + .5 * alpha * np.dot(w, w)
        sigma = signs * expit(-margin)
        grad_w = X.T.dot(sigma.sum(axis=0)) + alpha * w
        grad_theta = -sigma.sum(axis=1)
        grad_increments = np.cumsum(grad_theta[::-1])[::-1]
        return float(loss), np.r_[grad_w, grad_increments]

    def fit(self, X, y):
        X = np.asarray(X, dtype=float)
        y = np.asarray(y, dtype=int) - 1
        if not np.array_equal(np.unique(y), np.arange(10)):
            raise ValueError("Ordinal training requires all ten outcome categories.")
        self.classes_ = np.arange(1, 11)
        frequencies = np.bincount(y, minlength=10) / len(y)
        cumulative = np.clip(np.cumsum(frequencies)[:-1], 1e-6, 1 - 1e-6)
        theta = np.log(cumulative / (1 - cumulative))
        initial = np.r_[np.zeros(X.shape[1]), theta[0], np.diff(theta)]
        bounds = [(None, None)] * (X.shape[1] + 1) + [(0, None)] * 8
        result = minimize(self.objective, initial, args=(X, y, self.alpha), jac=True,
                          method="L-BFGS-B", bounds=bounds,
                          options={"maxiter": self.max_iter, "ftol": self.tol, "gtol": 1e-5})
        gradient = result.jac.copy()
        for i in range(X.shape[1] + 1, len(gradient)):
            if result.x[i] <= 1e-8 and gradient[i] >= 0:
                gradient[i] = 0
        projected = float(np.max(np.abs(gradient)) / len(y))
        if not result.success or projected > 1e-4:
            result = minimize(self.objective, result.x, args=(X, y, self.alpha), jac=True,
                              method="L-BFGS-B", bounds=bounds,
                              options={"maxiter": self.max_iter * 2, "ftol": 1e-12, "gtol": 1e-6})
            gradient = result.jac.copy()
            for i in range(X.shape[1] + 1, len(gradient)):
                if result.x[i] <= 1e-8 and gradient[i] >= 0:
                    gradient[i] = 0
            projected = float(np.max(np.abs(gradient)) / len(y))
        if not result.success or projected > 1e-4:
            raise RuntimeError(f"Ordinal solver failed: {result.message}; projected gradient/n={projected:g}")
        self.coef_ = result.x[:X.shape[1]]
        self.theta_ = np.cumsum(result.x[X.shape[1]:])
        self.optimization_ = {"solver": "L-BFGS-B", "success": bool(result.success),
                              "message": str(result.message), "iterations": int(result.nit),
                              "objective": float(result.fun), "projected_gradient_per_row": projected,
                              "max_iter": self.max_iter, "ftol_initial": self.tol}
        return self

    def predict_proba(self, X):
        cumulative = expit(self.theta_[None, :] - np.asarray(X).dot(self.coef_)[:, None])
        p = np.diff(np.column_stack((np.zeros(len(X)), cumulative, np.ones(len(X)))), axis=1)
        p = np.maximum(p, 0)
        return p / p.sum(axis=1, keepdims=True)

    def predict(self, X):
        return median_predictions(self.predict_proba(X))


def median_predictions(probabilities):
    return np.minimum((np.cumsum(probabilities, axis=1) < .5).sum(axis=1) + 1, 10)


def make_model(name, parameters=None, features=CORE):
    parameters = dict(parameters or {})
    random_state = parameters.pop("random_state", SEED)
    if name == "baseline":
        return EmpiricalBaseline()
    if name == "ordinal":
        estimator = OrdinalLogit(**parameters)
    elif name == "forest":
        estimator = RandomForestClassifier(n_estimators=200, random_state=random_state,
                                           n_jobs=1, **parameters)
    elif name == "boosting":
        estimator = HistGradientBoostingClassifier(max_iter=200, early_stopping=True,
                      validation_fraction=.15, n_iter_no_change=15, random_state=random_state,
                      categorical_features=None, **parameters)
    else:
        raise ValueError(f"Unknown model: {name}")
    return Pipeline([("encode", SurveyEncoder(features)), ("model", estimator)])
