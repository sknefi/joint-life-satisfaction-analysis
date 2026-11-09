"""Checkpointed, training-only tuning and frozen production validation."""

from __future__ import annotations

import hashlib
import importlib.metadata
import json
import platform
import time
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from joblib import Parallel, delayed
from sklearn.model_selection import GroupKFold, ParameterGrid, ParameterSampler
from threadpoolctl import threadpool_limits

from .config import CORE, DEMOGRAPHIC, SCHEMA_VERSION, SEED, TARGET, WITH_HAPPINESS
from . import __version__
from .data import clean_features, load_source, split_respondents, within_country_folds
from .metrics import reliability, scores
from .models import make_model, median_predictions


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n")
    temporary.replace(path)


def file_hash(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def versions():
    return {"python": platform.python_version(), **{name: importlib.metadata.version(name)
            for name in ("numpy", "scipy", "pandas", "scikit-learn", "pyarrow", "joblib")}}


def diagnostics(model):
    if not hasattr(model, "named_steps"):
        return {"criterion": "empirical frequency; median minimizes empirical absolute error",
                "median": int(median_predictions(model.probabilities_[None, :])[0]),
                "probabilities": model.probabilities_.tolist(),
                "probability_high_7_10": float(model.probabilities_[6:].sum())}
    estimator = model.named_steps["model"]
    encoding = model.named_steps["encode"]
    if hasattr(estimator, "optimization_"):
        return {**estimator.optimization_, "settings": estimator.get_params(), "coefficients": dict(zip(encoding.feature_names_, estimator.coef_.tolist())),
                "thresholds": estimator.theta_.tolist(), "expanded_features": len(encoding.feature_names_)}
    if hasattr(estimator, "estimators_"):
        return {"algorithm": "greedy CART, bootstrap aggregation", "settings": estimator.get_params(), "trees": len(estimator.estimators_),
                "total_nodes": int(sum(t.tree_.node_count for t in estimator.estimators_)),
                "max_observed_depth": int(max(t.tree_.max_depth for t in estimator.estimators_)),
                "feature_importance": dict(zip(encoding.feature_names_, estimator.feature_importances_.tolist())),
                "expanded_features": len(encoding.feature_names_)}
    return {"algorithm": "histogram gradient boosting", "settings": estimator.get_params(), "iterations": int(estimator.n_iter_),
            "trees": int(estimator.n_iter_ * estimator.n_trees_per_iteration_),
            "early_stopping": bool(estimator.do_early_stopping_),
            "validation_loss_initial": float(-estimator.validation_score_[0]),
            "validation_loss_final": float(-estimator.validation_score_[-1]),
            "expanded_features": len(encoding.feature_names_)}


def evaluate_fold(name, parameters, features, frame, train_ids, validation_ids):
    with threadpool_limits(limits=1):
        X = clean_features(frame, features)
        y = frame[TARGET].to_numpy(dtype=int)
        model = make_model(name, parameters, features)
        started = time.perf_counter()
        model.fit(X.iloc[train_ids], y[train_ids])
        p = model.predict_proba(X.iloc[validation_ids])
        if hasattr(model, "classes_") and not np.array_equal(model.classes_, np.arange(1, 11)):
            raise ValueError("Every fold must contain all ten response classes.")
        result = scores(y[validation_ids], p)
        result.update(seconds=time.perf_counter() - started, n_train=len(train_ids), n_validation=len(validation_ids))
        diag = diagnostics(model)
        return result, p, diag


def cross_validate(name, parameters, features, frame, folds, jobs):
    results = Parallel(n_jobs=jobs)(delayed(evaluate_fold)(name, parameters, features, frame, a, b) for a, b in folds)
    oof = np.empty((len(frame), 10))
    for (_, ids), (_, p, _) in zip(folds, results):
        oof[ids] = p
    metrics = [r[0] for r in results]
    maes = np.array([r["mae"] for r in metrics])
    summary = {"model": name, "parameters": parameters, "features": list(features),
               "mae": float(maes.mean()), "mae_se": float(maes.std(ddof=1) / np.sqrt(len(maes))),
               "log_loss": float(np.mean([r["log_loss"] for r in metrics])),
               "rps": float(np.mean([r["rps"] for r in metrics])),
               "high_brier": float(np.mean([r["high_brier"] for r in metrics])),
               "folds": metrics, "diagnostics": [r[2] for r in results]}
    return summary, oof


def initial_search():
    return {
        "ordinal": [{"alpha": a} for a in (.1, 1., 10., 100.)],
        "forest": list(ParameterGrid({"max_depth": [6, 10], "min_samples_leaf": [20, 50], "max_features": ["sqrt", .7]})),
        "boosting": list(ParameterSampler({"learning_rate": [.05, .1], "max_leaf_nodes": [7, 15],
                      "min_samples_leaf": [50, 100], "l2_regularization": [0., 1.]}, n_iter=8, random_state=SEED)),
    }


def boundary_extension(name, best):
    """One pre-specified outward extension, without opening a test set."""
    p = dict(best["parameters"])
    if name == "ordinal":
        if p["alpha"] == .1:
            return [{"alpha": .01}]
        if p["alpha"] == 100:
            return [{"alpha": 1000.}]
        return []
    if name == "forest":
        p["max_depth"] = 14 if p["max_depth"] == 10 else 4
        p["min_samples_leaf"] = 10 if p["min_samples_leaf"] == 20 else 100
        return [p]
    p["max_leaf_nodes"] = 23 if p["max_leaf_nodes"] == 15 else 3
    p["min_samples_leaf"] = 25 if p["min_samples_leaf"] == 50 else 200
    return [p]


def run_training(source, root, jobs=4):
    root = Path(root)
    results = root / "02_develop/results"
    private = root / "02_develop/local"
    models = root / "models"
    for path in (results, private, models):
        path.mkdir(parents=True, exist_ok=True)
    raw = load_source(source)
    labels, held = split_respondents(raw)
    raw.assign(partition=labels)[["uniqid", "partition"]].to_csv(private / "split_manifest.csv", index=False)
    training = raw.loc[labels.eq("train")].reset_index(drop=True)
    folds = within_country_folds(training)
    source_hash = file_hash(source)
    code_hash = hashlib.sha256(b"".join(p.read_bytes() for p in sorted(Path(__file__).parent.glob("*.py")))).hexdigest()
    identity = {"source_sha256": source_hash, "code_sha256": code_hash, "versions": versions(), "seed": SEED}
    identity_path = private / "run_identity.json"
    if identity_path.exists() and json.loads(identity_path.read_text()) != identity:
        raise ValueError("Checkpoint identity changed. Use a fresh local checkpoint directory before retraining.")
    write_json(identity_path, identity)
    split_summary = {"seed": SEED, "held_out_countries": held,
                     "training_countries": sorted(training.cntry_AN.unique().tolist()),
                     "counts": {str(k): int(v) for k, v in labels.value_counts().items()},
                     "test_evaluations": 0, "partition_rule": "country and target strata, floor(0.7*n), floor(0.8*n)"}
    write_json(results / "splits.json", split_summary)
    missing = []
    for field in (*CORE, "A008", TARGET):
        if field != "cntry_AN":
            for code in (-1, -2, -3, -4, -5):
                missing.append({"variable": field, "code": code, "n": int(raw[field].eq(code).sum())})
    pd.DataFrame(missing).to_csv(results / "missingness.csv", index=False)
    print(f"Training: {len(training):,}; held-out countries: {held}", flush=True)

    def trial(name, params, features=CORE, tag="within"):
        key = hashlib.sha256(json.dumps([name, params, list(features), tag], sort_keys=True).encode()).hexdigest()[:16]
        checkpoint = private / f"cv_{key}.joblib"
        if checkpoint.exists():
            return joblib.load(checkpoint)
        selected_folds = folds if tag == "within" else list(GroupKFold(5).split(training, groups=training.cntry_AN))
        print(f"CV {tag}: {name} {params}; {len(features)} inputs", flush=True)
        value = cross_validate(name, params, features, training, selected_folds, jobs)
        joblib.dump(value, checkpoint, compress=3)
        print(f"  MAE {value[0]['mae']:.4f} +/- {value[0]['mae_se']:.4f}", flush=True)
        return value

    trials, chosen, oofs = [], {}, {}
    base, base_oof = trial("baseline", {})
    trials.append(base)
    chosen["baseline"], oofs["baseline"] = base, base_oof
    for name, candidates in initial_search().items():
        current = []
        for p in candidates:
            summary, p_oof = trial(name, p)
            current.append((summary, p_oof))
        initial_best = min(current, key=lambda r: (r[0]["mae"], r[0]["rps"]))[0]
        for p in boundary_extension(name, initial_best):
            summary, p_oof = trial(name, p)
            summary["boundary_extension"] = True
            current.append((summary, p_oof))
        trials.extend(r[0] for r in current)
        chosen[name], oofs[name] = min(current, key=lambda r: (r[0]["mae"], r[0]["rps"]))
        write_json(results / "trials.json", trials)
    winner = min(chosen, key=lambda name: (chosen[name]["mae"], chosen[name]["rps"]))
    rule = "lowest mean CV MAE"
    if chosen["baseline"]["mae"] <= chosen[winner]["mae"]:
        winner, rule = "baseline", "no candidate improves on baseline"
    elif chosen["ordinal"]["mae"] <= chosen[winner]["mae"] + chosen[winner]["mae_se"]:
        winner, rule = "ordinal", "ordinal within one standard error of best MAE"
    # This decision is written before production validation is read.
    write_json(results / "selection.json", {"selected": winner, "rule": rule,
               "selected_before_production_validation": True,
               "candidates": [{k: v for k, v in row.items() if k not in ("diagnostics", "folds")}
                              for row in chosen.values()]})
    for name, params in [(n, row["parameters"]) for n, row in chosen.items()]:
        with threadpool_limits(limits=1):
            model = make_model(name, params)
            model.fit(clean_features(training), training[TARGET].to_numpy(dtype=int))
        joblib.dump(model, private / f"{name}.joblib", compress=3)
        write_json(results / f"{name}_parameters.json", diagnostics(model))
    selected_model = joblib.load(private / f"{winner}.joblib")
    bundle = {"schema_version": SCHEMA_VERSION, "package_version": __version__, "model_name": winner,
              "features": list(CORE), "countries": sorted(training.cntry_AN.unique().tolist()),
              "classes": list(range(1, 11)), "estimator": selected_model,
              "versions": versions(), "source_sha256": source_hash, "training_rows": len(training)}
    model_path = models / "evs_v0_1_0.joblib"
    joblib.dump(bundle, model_path, compress=3)
    write_json(models / "evs_v0_1_0.metadata.json", {k: v for k, v in bundle.items() if k != "estimator"} |
               {"artifact_sha256": file_hash(model_path), "selected_by": rule,
                "prediction_scope": "historical EVS-style records in the 30 training-country contexts"})
    sensitivity = []
    for label, features in (("demographic_economic", DEMOGRAPHIC), ("with_happiness", WITH_HAPPINESS)):
        summary, _ = trial(winner, chosen[winner]["parameters"], features)
        sensitivity.append({"specification": label, **summary})
    alternative_params = dict(chosen["forest"]["parameters"], criterion="entropy")
    alternative, _ = trial("forest", alternative_params)
    write_json(results / "sensitivity.json", sensitivity)
    write_json(results / "alternative_criterion.json", {"primary": chosen["forest"], "alternative": alternative,
               "interpretation": "Gini versus Shannon entropy are local greedy split criteria, not a globally optimized forest likelihood."})
    stability = []
    for name in ("forest", "boosting"):
        summary, _ = trial(name, dict(chosen[name]["parameters"], random_state=2026))
        stability.append({"model": name, "seed": 2026, "mae": summary["mae"],
                          "mae_original_seed": chosen[name]["mae"], "log_loss": summary["log_loss"],
                          "rps": summary["rps"], "purpose": "randomization sensitivity, not additional selection"})
    write_json(results / "seed_stability.json", stability)
    grouped = []
    for name in chosen:
        summary, _ = trial(name, chosen[name]["parameters"], tag="country")
        grouped.append(summary)
    write_json(results / "country_cv.json", grouped)
    production = raw.loc[labels.eq("production_validation")].reset_index(drop=True)
    p = selected_model.predict_proba(clean_features(production))
    production_scores = scores(production[TARGET].to_numpy(dtype=int), p)
    write_json(results / "production_validation.json", {"model": winner, "n": len(production),
               "scores": production_scores, "reliability": reliability(production[TARGET], p),
               "used_for_tuning": False, "intervals_displayed": False})
    X = clean_features(training)
    chosen_oof = oofs[winner]
    subgroup_rows = []
    for field in ("cntry_AN", "X001", "X025R", "X028"):
        for value, positions in training.groupby(field).indices.items():
            if len(positions) >= 30:
                subgroup_rows.append({"field": field, "value": str(value), "n": len(positions),
                                     **scores(training[TARGET].iloc[positions], chosen_oof[positions])})
    age_group = pd.cut(training.X003.where(training.X003.ge(18)), [17, 29, 44, 59, 81, 100], labels=["18-29", "30-44", "45-59", "60-81", "82+"])
    for value, positions in training.groupby(age_group, observed=True).indices.items():
        if len(positions) >= 30:
            subgroup_rows.append({"field": "age", "value": str(value), "n": len(positions),
                                 **scores(training[TARGET].iloc[positions], chosen_oof[positions])})
    pd.DataFrame(subgroup_rows).to_csv(results / "subgroup_cv.csv", index=False)
    write_json(results / "calibration_cv.json", reliability(training[TARGET], chosen_oof))
    write_json(results / "run.json", {**identity, "selected_model": winner,
               "training_rows": len(training), "prediction_test_evaluations": 0,
               "training_weighting": "unweighted respondent prediction; survey weighting used separately for inference"})
    print(f"Selected {winner}. Production validation MAE={production_scores['mae']:.4f}. Final tests unopened.", flush=True)
    return bundle
