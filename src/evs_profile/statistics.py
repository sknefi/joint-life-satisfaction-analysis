"""Pure statistical and formatting helpers for dataset profiles."""

from __future__ import annotations

import math
from collections import Counter
from typing import Iterable

from .config import KEY_VARIABLES, MISSING_CODES


def percentage(count: int, denominator: int) -> str:
    return f"{100 * count / denominator:.2f}%" if denominator else "n/a"


def human_bytes(byte_count: int) -> str:
    units = ("B", "KiB", "MiB", "GiB", "TiB")
    value = float(byte_count)
    for unit in units:
        if value < 1024 or unit == units[-1]:
            return f"{value:.1f} {unit}"
        value /= 1024
    raise AssertionError("unreachable")


def numeric_sort_key(value: str) -> tuple[int, float | str]:
    try:
        return (0, float(value))
    except ValueError:
        return (1, value)


def valid_counter(variable: str, counts: Counter[str]) -> Counter[str]:
    definition = KEY_VARIABLES[variable]
    result: Counter[str] = Counter()
    for value, count in counts.items():
        if value == "" or value in MISSING_CODES:
            continue
        try:
            numeric_value = int(value)
        except ValueError:
            continue
        if (
            definition.valid_min is not None
            and definition.valid_max is not None
            and definition.valid_min <= numeric_value <= definition.valid_max
        ):
            result[value] += count
    return result


def invalid_count(variable: str, counts: Counter[str]) -> int:
    definition = KEY_VARIABLES[variable]
    invalid = 0
    for value, count in counts.items():
        if value == "" or value in MISSING_CODES:
            continue
        try:
            numeric_value = int(value)
        except ValueError:
            invalid += count
            continue
        if not (
            definition.valid_min is not None
            and definition.valid_max is not None
            and definition.valid_min <= numeric_value <= definition.valid_max
        ):
            invalid += count
    return invalid


def median_from_counts(counts: Counter[str]) -> float:
    total = sum(counts.values())
    if total == 0:
        return math.nan
    positions = {(total - 1) // 2, total // 2}
    found: list[float] = []
    cumulative = 0
    for raw_value, count in sorted(
        counts.items(), key=lambda item: numeric_sort_key(item[0])
    ):
        next_cumulative = cumulative + count
        for position in sorted(positions):
            if cumulative <= position < next_cumulative:
                found.append(float(raw_value))
        cumulative = next_cumulative
    return sum(found) / len(found)


def variable_family_counts(columns: Iterable[str]) -> Counter[str]:
    groups: Counter[str] = Counter()
    for column in columns:
        if column.startswith("x"):
            groups["X - respondent demographics"] += 1
            continue
        prefix = column[0]
        if prefix == "A":
            groups["A - perceptions of life"] += 1
        elif prefix == "B":
            groups["B - environment"] += 1
        elif prefix == "C":
            groups["C - work"] += 1
        elif prefix == "D":
            groups["D - family"] += 1
        elif prefix in {"E", "Y"}:
            groups["E/Y - politics and society"] += 1
        elif prefix == "F":
            groups["F - religion and morale"] += 1
        elif prefix == "G":
            groups["G - national identity"] += 1
        elif prefix == "H":
            groups["H - security"] += 1
        elif prefix == "V":
            groups["V - parents' demographics"] += 1
        elif prefix == "W":
            groups["W - partner demographics"] += 1
        elif prefix == "X":
            groups["X - respondent demographics"] += 1
        else:
            groups["Administrative, ID, protocol and weights"] += 1
    return groups

