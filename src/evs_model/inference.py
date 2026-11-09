"""Pre-specified weighted descriptions with explicitly approximate intervals."""

from pathlib import Path

import numpy as np
import pandas as pd

from .config import SEED
from .data import load_source
from .training import file_hash, versions, write_json
from .audit_analysis import training_inference_frame


def weighted_summary(y, weights):
    y, weights = np.asarray(y, float), np.asarray(weights, float)
    valid = np.isfinite(y) & np.isfinite(weights) & (weights > 0)
    y, weights = y[valid], weights[valid]
    if not len(y):
        return {"estimate": None, "effective_n": 0., "n": 0}
    return {"estimate": float(np.average(y, weights=weights)),
            "effective_n": float(weights.sum() ** 2 / np.square(weights).sum()), "n": len(y)}


def run_inference(source, root, repetitions=1000):
    raw = load_source(source)
    frame, held = training_inference_frame(raw)
    y = frame.A170.ge(7).to_numpy(dtype=float)
    gw = frame.analysis_weight.to_numpy(dtype=float)
    eq = gw * frame.wght_eq1000.to_numpy(dtype=float)
    pop = gw * frame.pwght.to_numpy(dtype=float)
    groups = []

    def add(kind, value, mask, weights):
        groups.append((kind, str(value), np.asarray(mask), weights))

    for label, weights in (("unweighted", np.ones(len(frame))), ("equal_country", eq), ("population", pop)):
        add("overall", label, np.ones(len(frame), dtype=bool), weights)
    for country in sorted(frame.cntry_AN.unique()):
        country_mask = frame.cntry_AN.eq(country).to_numpy()
        add("country", country, country_mask, gw)
        for field, levels in (("X047E_EVS5", range(1, 11)), ("X028", range(1, 9))):
            for level in levels:
                add(f"country_{field}", f"{country}:{level}", country_mask & frame[field].eq(level).to_numpy(), gw)
    for field, levels in (("X047E_EVS5", range(1, 11)), ("X028", range(1, 9))):
        for level in levels:
            add(field, level, frame[field].eq(level).to_numpy(), eq)
    add("contrast_group", "income_low_1_2", frame.X047E_EVS5.isin([1, 2]).to_numpy(), eq)
    add("contrast_group", "income_high_9_10", frame.X047E_EVS5.isin([9, 10]).to_numpy(), eq)
    add("contrast_group", "paid_employment", frame.X028.isin([1, 2]).to_numpy(), eq)
    add("contrast_group", "unemployed", frame.X028.eq(7).to_numpy(), eq)
    rows, active_groups = [], []
    for kind, value, mask, weights in groups:
        summary = weighted_summary(y[mask], weights[mask])
        publish = summary["n"] >= 30 and summary["effective_n"] >= 30
        rows.append({"kind": kind, "value": value, **summary, "suppressed": not publish})
        active_groups.append((np.flatnonzero(mask), weights[mask]))
    # Multinomial counts reproduce an iid respondent bootstrap within each fixed
    # country without constructing 1000 full copies of the survey table.
    rng = np.random.default_rng(SEED)
    country_indices = list(frame.groupby("cntry_AN").indices.values())
    draws = np.empty((repetitions, len(groups)))
    for b in range(repetitions):
        multiplicity = np.zeros(len(frame), dtype=float)
        for ids in country_indices:
            multiplicity[ids] = np.bincount(rng.integers(0, len(ids), len(ids)), minlength=len(ids))
        for k, (ids, weights) in enumerate(active_groups):
            w = weights * multiplicity[ids]
            draws[b, k] = np.dot(y[ids], w) / w.sum() if w.sum() else np.nan
    for k, row in enumerate(rows):
        if row["suppressed"]:
            row.update(estimate=None, standard_error=None, ci_low=None, ci_high=None)
        else:
            row.update(standard_error=float(np.nanstd(draws[:, k], ddof=1)),
                       ci_low=float(np.nanquantile(draws[:, k], .025)), ci_high=float(np.nanquantile(draws[:, k], .975)))
    names = {(r["kind"], r["value"]): i for i, r in enumerate(rows)}
    contrasts = []
    for label, a, b in (("income_high_minus_low", "income_high_9_10", "income_low_1_2"),
                         ("paid_minus_unemployed", "paid_employment", "unemployed")):
        ia, ib = names[("contrast_group", a)], names[("contrast_group", b)]
        values = draws[:, ia] - draws[:, ib]
        contrasts.append({"contrast": label, "estimate": rows[ia]["estimate"] - rows[ib]["estimate"],
                          "standard_error": float(values.std(ddof=1)),
                          "ci_low": float(np.quantile(values, .025)), "ci_high": float(np.quantile(values, .975)),
                          "causal": False})
    result_path = Path(root) / "02_develop/results"
    result_path.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(result_path / "weighted_proportions.csv", index=False)
    write_json(result_path / "inference.json", {"bootstrap_repetitions": repetitions, "seed": SEED,
               "source_parquet_sha256": file_hash(source), "versions": versions(),
               "interval_method": "percentile iid respondent bootstrap within fixed countries; approximate, not full survey-design intervals",
               "limitations": "No definitive PSU/stratum identifiers; within-country cluster dependence, nonresponse and measurement bias are not repaired.",
               "contrasts": contrasts, "overall": [r for r in rows if r["kind"] == "overall"],
               "missing_income_fraction": float(raw.X047E_EVS5.lt(0).mean()),
               "analysis_n": len(frame), "analysis_partition": "train only", "excluded_countries": held,
               "split_probability_min": float(frame.split_probability.min()),
               "split_probability_max": float(frame.split_probability.max()),
               "weight_rule": "gwght / P(train | country, A170); multiply by country-size factor for pooling",
               "population_scope": "30 training-country EVS populations, private-household adults, 2017-2021; conditional on target-response assumptions"})
    distribution = frame.groupby("A170", observed=True).apply(lambda d: pd.Series({"n": len(d), "equal_country_weight": (d.analysis_weight * d.wght_eq1000).sum()}), include_groups=False)
    distribution["unweighted_proportion"] = distribution.n / distribution.n.sum()
    distribution["equal_country_proportion"] = distribution.equal_country_weight / distribution.equal_country_weight.sum()
    distribution.to_csv(result_path / "target_distribution.csv")
    # Income complete-case sensitivity, a description rather than an MNAR repair.
    complete = frame.X047E_EVS5.between(1, 10).to_numpy()
    write_json(result_path / "income_sensitivity.json", {
        "income_observed": weighted_summary(y[complete], eq[complete]),
        "income_missing": weighted_summary(y[~complete], eq[~complete]),
        "training_missing_income_fraction": float(frame.X047E_EVS5.lt(0).mean()),
        "interpretation": "A difference flags selection risk; neither imputation nor weighting identifies an MNAR correction."})
    print(f"Inference: {len(frame):,} valid outcomes, {repetitions} stratified respondent bootstrap draws.", flush=True)
