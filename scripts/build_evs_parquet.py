#!/usr/bin/env python3
"""Create the reproducible EVS Parquet dataset from the immutable joint CSV."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
DEFAULT_SOURCE = PROJECT_ROOT / "data" / "raw" / "evs_wvs_dataset.csv"
DEFAULT_OUTPUT = PROJECT_ROOT / "data" / "processed" / "evs_v5_0.parquet"

sys.path.insert(0, str(SRC_ROOT))

from evs_profile.dataset import build_evs_parquet  # noqa: E402
from evs_profile.statistics import human_bytes  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build and validate the EVS-only Parquet dataset."
    )
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        result = build_evs_parquet(args.source, args.output)
    except (OSError, ValueError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1

    print(f"Created: {args.output.resolve()}")
    print(f"Rows: {result.rows:,}")
    print(f"Columns: {result.columns:,}")
    print(f"Dropped WVS-only columns: {', '.join(result.dropped_columns)}")
    print(f"Parquet size: {result.parquet_bytes:,} bytes ({human_bytes(result.parquet_bytes)})")
    print(f"Compression: {result.compression}")
    print(f"Source SHA-256: {result.source_sha256}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
