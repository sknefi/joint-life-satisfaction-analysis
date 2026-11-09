"""Outcome-scale error, proper probability scores and reliability summaries."""

import numpy as np
from sklearn.metrics import log_loss

from .models import median_predictions


def scores(y, probabilities):
    y = np.asarray(y, dtype=int)
    p = np.asarray(probabilities, dtype=float)
    if p.shape != (len(y), 10) or not np.isfinite(p).all() or (p < 0).any() or not np.allclose(p.sum(1), 1):
        raise ValueError("Expected finite n x 10 non-negative probabilities summing to one.")
    predicted = median_predictions(p)
    cumulative = p.cumsum(axis=1)[:, :-1]
    observed_cumulative = y[:, None] <= np.arange(1, 10)[None, :]
    return {"mae": float(np.abs(y - predicted).mean()),
            "log_loss": float(log_loss(y, np.clip(p, 1e-15, 1), labels=np.arange(1, 11))),
            "rps": float(np.mean((cumulative - observed_cumulative) ** 2)),
            "high_brier": float(np.mean((p[:, 6:].sum(1) - (y >= 7)) ** 2))}


def reliability(y, p, bins=10):
    high = p[:, 6:].sum(axis=1)
    assignment = np.minimum((high * bins).astype(int), bins - 1)
    rows = []
    for k in range(bins):
        mask = assignment == k
        if mask.any():
            rows.append({"bin": k, "n": int(mask.sum()), "predicted": float(high[mask].mean()),
                         "observed": float((np.asarray(y)[mask] >= 7).mean())})
    return rows
