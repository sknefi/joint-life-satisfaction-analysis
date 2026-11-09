"""Installed commands with atomic, validated batch prediction."""

import argparse
import json
import sys
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

from .config import SCHEMA_VERSION
from .data import clean_features
from .models import median_predictions


def load_bundle(path):
    # Only load the project's trusted, versioned artifact; joblib is not a data
    # interchange format for arbitrary uploads.
    bundle = joblib.load(path)
    if bundle.get("schema_version") != SCHEMA_VERSION or bundle.get("classes") != list(range(1, 11)):
        raise ValueError("Unsupported model artifact schema or class ordering.")
    return bundle


def predict_frame(bundle, frame):
    if frame.empty:
        raise ValueError("Input must contain at least one respondent.")
    X = clean_features(frame, bundle["features"], countries=bundle["countries"], strict=True)
    probabilities = bundle["estimator"].predict_proba(X)
    if not np.isfinite(probabilities).all() or (probabilities < 0).any() or not np.allclose(probabilities.sum(1), 1):
        raise ValueError("Model produced invalid probabilities.")
    result = pd.DataFrame({"predicted_score": median_predictions(probabilities),
                           "probability_high_7_10": probabilities[:, 6:].sum(1)})
    for i in range(10):
        result[f"p_{i + 1}"] = probabilities[:, i]
    return result


def predict_main(argv=None):
    parser = argparse.ArgumentParser(description="Predict historical EVS-style life satisfaction from a trusted local model.")
    parser.add_argument("--model", type=Path, default=Path("models/evs_v0_1_0.joblib"))
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        if args.input.resolve() == args.output.resolve():
            raise ValueError("Input and output paths must differ.")
        predictions = predict_frame(load_bundle(args.model), pd.read_csv(args.input))
        args.output.parent.mkdir(parents=True, exist_ok=True)
        temp = args.output.with_suffix(args.output.suffix + ".tmp")
        predictions.to_csv(temp, index=False)
        temp.replace(args.output)
    except (OSError, ValueError, KeyError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
    print(f"Predicted {len(predictions)} respondents; saved {args.output}")
    return 0


def train_main(argv=None):
    from .training import run_training
    parser = argparse.ArgumentParser(description="Training-only CV; never evaluates the final prediction tests.")
    parser.add_argument("--source", type=Path, default=Path("data/processed/evs_v5_0.parquet"))
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--jobs", type=int, default=4)
    args = parser.parse_args(argv)
    run_training(args.source, args.root, args.jobs)
    return 0


def infer_main(argv=None):
    from .inference import run_inference
    parser = argparse.ArgumentParser(description="Weighted descriptive inference with approximate bootstrap uncertainty.")
    parser.add_argument("--source", type=Path, default=Path("data/processed/evs_v5_0.parquet"))
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--bootstrap", type=int, default=1000)
    args = parser.parse_args(argv)
    if args.bootstrap < 2:
        parser.error("--bootstrap must be at least 2")
    run_inference(args.source, args.root, args.bootstrap)
    return 0
