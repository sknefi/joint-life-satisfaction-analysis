#!/usr/bin/env python3
"""Command-line entry point for the Joint EVS/WVS dataset profiler."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
DEFAULT_CSV = PROJECT_ROOT / "data" / "raw" / "evs_wvs_dataset.csv"
DEFAULT_PARQUET = PROJECT_ROOT / "data" / "processed" / "evs_v5_0.parquet"

# Allow direct execution without installing the local package.
sys.path.insert(0, str(SRC_ROOT))

from evs_profile.config import STUDY_OPTIONS  # noqa: E402
from evs_profile.reader import profile_csv  # noqa: E402
from evs_profile.report import render_report  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Print a report-ready Markdown profile of the Joint EVS/WVS CSV."
    )
    parser.add_argument(
        "--csv",
        type=Path,
        default=DEFAULT_CSV,
        help=f"CSV to inspect (default: {DEFAULT_CSV})",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Optional Markdown output file. The report is always printed to stdout.",
    )
    parser.add_argument(
        "--study",
        choices=STUDY_OPTIONS,
        default="EVS",
        help="Analytical subset to profile (default: EVS). Use 'all' for the complete joint dataset.",
    )
    parser.add_argument(
        "--parquet",
        type=Path,
        default=DEFAULT_PARQUET,
        help="Derived EVS Parquet whose actual size should be included when available.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        csv_path = args.csv.expanduser().resolve()
        profile = profile_csv(csv_path, STUDY_OPTIONS[args.study])
        parquet_path = args.parquet.expanduser().resolve()
        report = render_report(csv_path, profile, args.study, parquet_path)
    except (OSError, ValueError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1

    print(report)
    if args.output:
        output_path = args.output.expanduser().resolve()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(report + "\n", encoding="utf-8")
        print(f"\nSaved Markdown report to: {output_path}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
