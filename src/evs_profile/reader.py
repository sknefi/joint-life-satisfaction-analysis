"""Streaming CSV reader and profile accumulators."""

from __future__ import annotations

import csv
import math
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

from .config import KEY_VARIABLES, MISSING_CODES, STUDY_LABELS, WEIGHT_VARIABLES


@dataclass
class NumericSummary:
    count: int = 0
    total: float = 0.0
    minimum: float = math.inf
    maximum: float = -math.inf

    def add(self, raw_value: str) -> None:
        try:
            value = float(raw_value)
        except (TypeError, ValueError):
            return
        self.count += 1
        self.total += value
        self.minimum = min(self.minimum, value)
        self.maximum = max(self.maximum, value)

    @property
    def mean(self) -> float:
        return self.total / self.count if self.count else math.nan


@dataclass
class Profile:
    columns: list[str]
    source_row_count: int = 0
    row_count: int = 0
    selected_csv_bytes: int | None = None
    blank_cells: int = 0
    missing_counts: Counter[str] = field(default_factory=Counter)
    column_valid_counts: Counter[str] = field(default_factory=Counter)
    key_counts: dict[str, Counter[str]] = field(default_factory=dict)
    study_counts: Counter[str] = field(default_factory=Counter)
    year_counts: Counter[str] = field(default_factory=Counter)
    mode_counts: Counter[str] = field(default_factory=Counter)
    country_counts: Counter[str] = field(default_factory=Counter)
    country_study_counts: Counter[tuple[str, str]] = field(default_factory=Counter)
    uniqids: set[str] = field(default_factory=set)
    duplicate_uniqids: int = 0
    weight_summaries: dict[str, NumericSummary] = field(default_factory=dict)
    income_by_study: dict[tuple[str, str], Counter[str]] = field(default_factory=dict)


def profile_csv(csv_path: Path, study_code: str | None = "1") -> Profile:
    """Stream a CSV and calculate statistics for one study or the full joint file."""

    if not csv_path.is_file():
        raise FileNotFoundError(f"CSV not found: {csv_path}")

    with csv_path.open("r", encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        if reader.fieldnames is None:
            raise ValueError("The CSV has no header row.")

        columns = list(reader.fieldnames)
        required = {
            "study",
            "uniqid",
            "cntry_AN",
            "year",
            "mode",
            *KEY_VARIABLES,
            *WEIGHT_VARIABLES,
        }
        missing_columns = sorted(required - set(columns))
        if missing_columns:
            raise ValueError(f"Required columns are missing: {', '.join(missing_columns)}")

        profile = Profile(
            columns=columns,
            key_counts={name: Counter() for name in KEY_VARIABLES},
            weight_summaries={name: NumericSummary() for name in WEIGHT_VARIABLES},
            income_by_study={
                (study, variable): Counter()
                for study in STUDY_LABELS
                for variable in ("X047_WVS7", "X047E_EVS5")
            },
        )

        for row in reader:
            profile.source_row_count += 1
            study = row["study"]
            if study_code is not None and study != study_code:
                continue

            profile.row_count += 1

            for column, value in row.items():
                if value is None or value == "":
                    profile.blank_cells += 1
                elif value in MISSING_CODES:
                    profile.missing_counts[value] += 1
                else:
                    profile.column_valid_counts[column] += 1

            country = row["cntry_AN"]
            profile.study_counts[study] += 1
            profile.year_counts[row["year"]] += 1
            profile.mode_counts[row["mode"]] += 1
            profile.country_counts[country] += 1
            profile.country_study_counts[(country, study)] += 1

            uniqid = row["uniqid"]
            if uniqid in profile.uniqids:
                profile.duplicate_uniqids += 1
            else:
                profile.uniqids.add(uniqid)

            for variable in KEY_VARIABLES:
                profile.key_counts[variable][row[variable]] += 1

            for variable in WEIGHT_VARIABLES:
                value = row[variable]
                if value not in MISSING_CODES and value != "":
                    profile.weight_summaries[variable].add(value)

            for variable in ("X047_WVS7", "X047E_EVS5"):
                value = row[variable]
                category = value if value in MISSING_CODES or value == "" else "valid"
                profile.income_by_study[(study, variable)][category] += 1

    if profile.row_count == 0:
        requested = STUDY_LABELS.get(study_code or "", "requested scope")
        raise ValueError(f"No rows found for {requested}.")

    profile.selected_csv_bytes = _measure_selected_csv_bytes(
        csv_path, study_code, profile.row_count
    )
    return profile


def _measure_selected_csv_bytes(
    csv_path: Path, study_code: str | None, expected_rows: int
) -> int | None:
    """Measure a header-plus-selected-rows copy without creating that copy.

    The supplied EVS/WVS CSV stores one complete respondent per physical line and
    places ``study`` in the first column. If a future input violates that layout,
    return ``None`` rather than report a misleading size.
    """

    if study_code is None:
        return csv_path.stat().st_size

    prefix = study_code.encode("ascii") + b","
    selected_rows = 0
    selected_bytes = 0
    with csv_path.open("rb") as stream:
        header = stream.readline()
        selected_bytes += len(header)
        for line in stream:
            if line.startswith(prefix):
                selected_rows += 1
                selected_bytes += len(line)

    if selected_rows != expected_rows:
        return None
    return selected_bytes
