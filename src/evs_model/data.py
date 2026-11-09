"""Input validation, immutable source loading and deterministic split manifests."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

from .config import CORE, MISSING, SEED, SUPPORT, TARGET


def load_source(path):
    frame = pq.read_table(path).to_pandas()
    if not frame["study"].eq(1).all() or frame["uniqid"].duplicated().any():
        raise ValueError("Expected unique EVS respondents (study == 1).")
    return frame


def clean_features(frame, features=CORE, *, countries=None, strict=False):
    """Validate before converting documented missing codes into NaN.

    Administrative columns are accepted for internal training only; public input
    rejects them so that an accidentally supplied target cannot be used.
    """
    missing_columns = sorted(set(features) - set(frame.columns))
    if missing_columns:
        raise ValueError(f"Missing required columns: {', '.join(missing_columns)}")
    if strict:
        forbidden = {TARGET, "uniqid", "gwght", "pwght", "wght_eq1000", "study"} & set(frame.columns)
        if forbidden:
            raise ValueError(f"Remove target/administrative columns: {', '.join(sorted(forbidden))}")
        unexpected = set(frame.columns) - set(features)
        if unexpected:
            raise ValueError(f"Unexpected columns: {', '.join(sorted(unexpected))}")
    out = frame.loc[:, list(features)].copy()
    for name in features:
        if name == "cntry_AN":
            values = out[name].astype("string").str.strip().str.upper()
            if values.isna().any() or values.eq("").any():
                raise ValueError("cntry_AN is required for every respondent.")
            if countries is not None:
                unknown = sorted(set(values) - set(countries))
                if unknown:
                    raise ValueError(f"Unsupported countries: {', '.join(unknown)}")
            out[name] = values.astype(str)
            continue
        original = out[name]
        values = pd.to_numeric(original, errors="coerce")
        malformed = original.notna() & original.astype(str).str.strip().ne("") & values.isna()
        if malformed.any():
            raise ValueError(f"{name}: non-numeric survey code.")
        low, high = SUPPORT[name]
        valid = values.isna() | values.isin(MISSING) | (values.between(low, high) & values.mod(1).eq(0))
        if not valid.all():
            examples = values[~valid].head(3).tolist()
            raise ValueError(f"{name}: expected integer {low}..{high}, blank, or -1..-5; got {examples}")
        out[name] = values.mask(values.isin(MISSING)).astype(float)
    return out


def split_respondents(frame, seed=SEED, holdout_count=6):
    """Select countries without Y; split valid cases within country and Y strata."""
    rng = np.random.default_rng(seed)
    countries = np.array(sorted(frame.cntry_AN.unique()))
    if len(countries) <= holdout_count:
        raise ValueError("Need more countries than the requested country holdout.")
    held = sorted(rng.choice(countries, size=holdout_count, replace=False).tolist())
    labels = pd.Series("target_missing", index=frame.index, dtype=object)
    valid = frame[TARGET].between(1, 10)
    labels.loc[valid & frame.cntry_AN.isin(held)] = "country_test"
    known = frame.loc[valid & ~frame.cntry_AN.isin(held)]
    for _, block in known.groupby(["cntry_AN", TARGET], sort=True):
        ids = rng.permutation(block.index)
        n = len(ids)
        train_end, validation_end = int(n * .7), int(n * .8)
        labels.loc[ids[:train_end]] = "train"
        labels.loc[ids[train_end:validation_end]] = "production_validation"
        labels.loc[ids[validation_end:]] = "same_country_test"
    return labels, held


def within_country_folds(frame, n_splits=5, seed=SEED):
    rng = np.random.default_rng(seed)
    assignment = np.empty(len(frame), dtype=int)
    positional = frame.reset_index(drop=True)
    for _, block in positional.groupby(["cntry_AN", TARGET], sort=True):
        positions = rng.permutation(block.index)
        assignment[positions] = np.arange(len(positions)) % n_splits
    return [(np.flatnonzero(assignment != k), np.flatnonzero(assignment == k)) for k in range(n_splits)]
