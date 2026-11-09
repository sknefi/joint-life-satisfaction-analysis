"""Training-only audit supplements; never reselect the frozen production model."""

from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from scipy.linalg import lstsq, qr
from scipy.optimize import minimize
from threadpoolctl import threadpool_limits

from .config import CORE, TARGET
from .data import clean_features, load_source, split_respondents, within_country_folds
from .metrics import scores
from .models import SurveyEncoder, make_model
from .training import cross_validate, diagnostics, write_json


def training_inference_frame(raw):
    """Training countries only, with inverse split-selection probabilities.

    The partition is stratified on country x A170; rounding means its retention
    probabilities are not exactly 0.7. Counts define that partition design only;
    no held-out respondent's weights, predictors or outcome enters a fitted ratio.
    """
    labels, held = split_respondents(raw)
    eligible = raw.loc[raw[TARGET].between(1, 10) & ~raw.cntry_AN.isin(held)]
    full_counts = eligible.groupby(["cntry_AN", TARGET]).size()
    selected = raw.loc[labels.eq("train")].copy()
    selected_counts = selected.groupby(["cntry_AN", TARGET]).size().reindex(full_counts.index, fill_value=0)
    if selected_counts.eq(0).any():
        raise ValueError("A country-outcome stratum has zero training selection probability.")
    probabilities = selected_counts / full_counts
    index = pd.MultiIndex.from_frame(selected[["cntry_AN", TARGET]])
    selected["split_probability"] = probabilities.reindex(index).to_numpy()
    selected["analysis_weight"] = selected.gwght / selected.split_probability
    return selected.reset_index(drop=True), held


def huber_objective(coef, design, y, delta=1.):
    residual = design @ coef - y
    magnitude = np.abs(residual)
    loss = np.where(magnitude <= delta, .5 * residual**2, delta * (magnitude - .5 * delta))
    gradient = design.T @ np.clip(residual, -delta, delta) / len(y)
    return float(loss.mean()), gradient


def fit_loss_pair(X_train, y_train, X_validation):
    """Identical linear function class; change only squared versus Huber loss."""
    encoder = SurveyEncoder().fit(X_train)
    train = np.column_stack((np.ones(len(X_train)), encoder.transform(X_train)))
    valid = np.column_stack((np.ones(len(X_validation)), encoder.transform(X_validation)))
    # Select a full-rank basis from TRAINING data, resolving redundant one-hot
    # columns without changing the shared linear function class.
    _, R, pivots = qr(train, mode="economic", pivoting=True)
    diagonal = np.abs(np.diag(R))
    tolerance = np.finfo(float).eps * max(train.shape) * diagonal.max()
    rank = int((diagonal > tolerance).sum())
    columns = pivots[:rank]
    train, valid = train[:, columns], valid[:, columns]
    coef, _, _, _ = lstsq(train, y_train)
    optimized = minimize(huber_objective, coef, args=(train, y_train, 1.), jac=True,
                         method="L-BFGS-B", options={"maxiter": 3000, "ftol": 1e-12, "gtol": 1e-7})
    gradient = float(np.max(np.abs(optimized.jac)))
    if not optimized.success or gradient > 1e-5:
        raise RuntimeError(f"Huber audit fit did not converge: {optimized.message}; gradient={gradient}")
    names = np.array(["intercept", *encoder.feature_names_])[columns]
    detail = {"rank": rank, "delta": 1., "initial_values": "OLS solution on the same full-rank basis",
              "ols_coefficients": dict(zip(names.tolist(), coef.tolist())),
              "huber_coefficients": dict(zip(names.tolist(), optimized.x.tolist())),
              "huber_objective": float(optimized.fun), "huber_iterations": int(optimized.nit),
              "huber_gradient_max": gradient, "huber_success": bool(optimized.success),
              "solver": "scipy.linalg.lstsq (OLS); scipy.optimize.minimize L-BFGS-B (Huber)",
              "ftol": 1e-12, "gtol": 1e-7, "maxiter": 3000}
    # Both point rules use the same declared support restriction.
    return np.clip(valid @ coef, 1, 10), np.clip(valid @ optimized.x, 1, 10), detail


def run_audit_supplements(source, root, jobs=4):
    root = Path(root)
    raw = load_source(source)
    labels, _ = split_respondents(raw)
    training = raw.loc[labels.eq("train")].reset_index(drop=True)
    X, y = clean_features(training), training[TARGET].to_numpy(dtype=float)
    folds = within_country_folds(training)
    squared, huber = np.empty(len(y)), np.empty(len(y))
    details = []
    for k, (a, b) in enumerate(folds):
        print(f"Loss sensitivity fold {k + 1}/5", flush=True)
        with threadpool_limits(limits=1):
            squared[b], huber[b], detail = fit_loss_pair(X.iloc[a], y[a], X.iloc[b])
        details.append(detail)
    with threadpool_limits(limits=1):
        _, _, full = fit_loss_pair(X, y, X.iloc[:3])
    def point_metrics(p):
        return {"mae": float(np.abs(p - y).mean()), "mse": float(np.mean((p - y)**2))}
    write_json(root / "02_develop/results/loss_sensitivity.json", {
        "scope": "training-only, five existing within-country folds; diagnostic, not model selection",
        "numeric_outcome_assumption": "Score distances are treated as numeric only in this auxiliary sensitivity.",
        "squared": point_metrics(squared), "huber": point_metrics(huber),
        "mean_absolute_prediction_change": float(np.abs(squared - huber).mean()),
        "p95_absolute_prediction_change": float(np.quantile(np.abs(squared - huber), .95)),
        "same_function_class": True, "huber_delta_fixed_not_tuned": 1.,
        "fold_diagnostics": details, "full_training_parameters": full,
        "no_test_or_production_validation_used": True})
    selection = __import__("json").loads((root / "02_develop/results/selection.json").read_text())
    chosen = {r["model"]: r["parameters"] for r in selection["candidates"]}
    stability = []
    for name in ("forest", "boosting"):
        for seed in (42, 2026, 2027):
            params = dict(chosen[name], random_state=seed)
            print(f"Seed stability: {name}, seed={seed}", flush=True)
            summary, _ = cross_validate(name, params, CORE, training, folds, jobs)
            with threadpool_limits(limits=1):
                estimator = make_model(name, params).fit(X, y.astype(int))
                training_scores = scores(y, estimator.predict_proba(X))
            stability.append({"model": name, "seed": seed, "cv_mae": summary["mae"],
                              "cv_log_loss": summary["log_loss"], "training_log_loss": training_scores["log_loss"],
                              "diagnostics": diagnostics(estimator), "purpose": "fixed-configuration stability; no reselection"})
    write_json(root / "02_develop/results/seed_stability_extended.json", stability)
    print("Audit supplements complete. Frozen release model and validation scores unchanged.", flush=True)
