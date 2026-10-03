#!/usr/bin/env python3
"""Create a report-ready profile of the Joint EVS/WVS raw CSV.

The script is intentionally read-only and uses only Python's standard library.
It streams the CSV, so it does not need to load the whole dataset into memory.

Examples:
    python scripts/profile_dataset.py
    python scripts/profile_dataset.py --output reports/data_profile.md
    python scripts/profile_dataset.py --csv /path/to/another/version.csv
"""

from __future__ import annotations

import argparse
import csv
import math
import sys
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CSV = PROJECT_ROOT / "data" / "raw" / "evs_wvs_dataset.csv"

MISSING_CODES = {
    "-1": "Don't know",
    "-2": "No answer",
    "-3": "Not applicable",
    "-4": "Not asked in survey",
    "-5": "Missing: Other",
}

STUDY_LABELS = {"1": "EVS", "2": "WVS"}

MODE_LABELS = {
    "1": "Computer-Assisted Personal Interviewing (CAPI)",
    "2": "Paper-and-Pencil Interviewing (PAPI)",
    "3": "Computer-Assisted Web Interviewing (CAWI)",
    "4": "Mail/Post",
    "5": "Computer-Assisted Telephone Interviewing (CATI)",
    "6": "Web-based interview",
}


@dataclass(frozen=True)
class VariableDefinition:
    label: str
    statistical_type: str
    valid_min: int | None = None
    valid_max: int | None = None
    note: str = ""


KEY_VARIABLES: dict[str, VariableDefinition] = {
    "A170": VariableDefinition(
        "Satisfaction with your life",
        "Ordinal, bounded 1-10 (candidate Y)",
        1,
        10,
        "Treating this as continuous is a modelling assumption.",
    ),
    "A008": VariableDefinition("Feeling of happiness", "Ordinal categorical", 1, 4),
    "A009": VariableDefinition("Subjective state of health", "Ordinal categorical", 1, 5),
    "A165": VariableDefinition("Most people can be trusted", "Binary categorical", 1, 2),
    "A173": VariableDefinition("Freedom of choice and control", "Ordinal, bounded 1-10", 1, 10),
    "X001": VariableDefinition("Sex", "Nominal categorical", 1, 2),
    "X003": VariableDefinition(
        "Age", "Integer; upper-censored/top-coded", 16, 82, "82 means 82 or older."
    ),
    "X007": VariableDefinition("Marital status", "Nominal categorical", 1, 6),
    "X011": VariableDefinition(
        "Number of children", "Capped count", 0, 5, "5 means 5 or more children."
    ),
    "X013": VariableDefinition(
        "Number of people in household", "Capped count", 1, 6, "6 means 6 or more people."
    ),
    "X025A_01": VariableDefinition(
        "Highest education attained (ISCED)", "Ordinal categorical", 0, 8
    ),
    "X025R": VariableDefinition("Recoded educational level", "Ordinal categorical", 1, 3),
    "X028": VariableDefinition("Employment status", "Nominal categorical", 1, 8),
    "X047_WVS7": VariableDefinition(
        "WVS7 income scale",
        "Ordinal, source-specific",
        1,
        10,
        "Subjective position from the lowest to highest income group in the country.",
    ),
    "X047E_EVS5": VariableDefinition(
        "EVS5 income scale",
        "Ordinal, source-specific",
        1,
        10,
        "Net household-income deciles; do not automatically merge with X047_WVS7.",
    ),
}

WEIGHT_VARIABLES = ("gwght", "pwght", "wght_eq1000")
TOP_CODED_VARIABLES = {"X003": "82", "X011": "5", "X013": "6"}


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
    row_count: int = 0
    blank_cells: int = 0
    missing_counts: Counter[str] = field(default_factory=Counter)
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
    return parser.parse_args()


def profile_csv(csv_path: Path) -> Profile:
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
            profile.row_count += 1

            # Global CSV missing-code profile. The official file represents
            # missingness with negative codes rather than empty fields.
            for value in row.values():
                if value is None or value == "":
                    profile.blank_cells += 1
                elif value in MISSING_CODES:
                    profile.missing_counts[value] += 1

            study = row["study"]
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
                value = row[variable]
                profile.key_counts[variable][value] += 1

            for variable in WEIGHT_VARIABLES:
                value = row[variable]
                if value not in MISSING_CODES and value != "":
                    profile.weight_summaries[variable].add(value)

            for variable in ("X047_WVS7", "X047E_EVS5"):
                value = row[variable]
                category = value if value in MISSING_CODES or value == "" else "valid"
                profile.income_by_study[(study, variable)][category] += 1

    return profile


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
    for raw_value, count in sorted(counts.items(), key=lambda item: numeric_sort_key(item[0])):
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


def render_report(csv_path: Path, profile: Profile) -> str:
    n = profile.row_count
    p = len(profile.columns)
    raw_size = csv_path.stat().st_size
    dense_numeric_bytes = n * p * 8
    total_cells = n * p
    families = variable_family_counts(profile.columns)
    source_specific_evs = sum(column.endswith("_EVS5") for column in profile.columns)
    source_specific_wvs = sum(column.endswith("_WVS7") for column in profile.columns)

    lines: list[str] = []
    add = lines.append
    add("# Joint EVS/WVS 2017-2022: data profile")
    add("")
    add(f"- CSV inspected: `{csv_path.resolve()}`")
    add("- Dataset: Joint EVS/WVS 2017-2022, Version 5.0.0")
    add("- Producers: European Values Study and World Values Survey")
    add("- GESIS DOI: <https://doi.org/10.4232/1.14320>")
    add("- WVSA DOI: <https://doi.org/10.14281/18241.26>")
    add("- Licence/terms: not stated in the supplied Variable Report; verify the official access page before submission.")
    add("")

    add("## 1. Size and computational profile")
    add("")
    add("| Quantity | Result |")
    add("|---|---:|")
    add(f"| Rows / observations (`n`) | {n:,} |")
    add(f"| Delivered columns (`p`) | {p:,} |")
    add(f"| Maximum non-target columns if `Y = A170` | {p - 1:,} |")
    add(f"| `n / p` | {n / p:,.1f} |")
    add(f"| Files / tables | 1 CSV file / 1 table |")
    add(f"| Raw file size | {raw_size:,} bytes ({human_bytes(raw_size)}) |")
    add(f"| Dense 8-byte matrix baseline | {human_bytes(dense_numeric_bytes)} plus software/string overhead |")
    add("")
    add(
        "Interpretation: the file fits comfortably in ordinary laptop memory, and this script can also "
        "profile it as a stream. The dataset is much larger in `n` than in `p`; computational size is "
        "not the main modelling difficulty. The final predictor count will be below 230 before encoding "
        "because IDs, protocol variables, weights, and the target are not ordinary predictors."
    )
    add("")

    add("### Variable families")
    add("")
    add("| Family | Columns |")
    add("|---|---:|")
    for family, count in families.items():
        add(f"| {family} | {count:,} |")
    add(f"| Names ending in `_EVS5` (overlaps families above) | {source_specific_evs:,} |")
    add(f"| Names ending in `_WVS7` (overlaps families above) | {source_specific_wvs:,} |")
    add("")

    add("## 2. Observational structure and coverage")
    add("")
    add("- One row represents one survey respondent.")
    add("- Structure: hierarchical pooled cross-sections, not a longitudinal panel of repeatedly observed people.")
    add(f"- Unique `uniqid` values: {len(profile.uniqids):,}; duplicate IDs: {profile.duplicate_uniqids:,}.")
    add(f"- Countries/territories: {len(profile.country_counts):,}.")
    add(f"- Country-study samples: {len(profile.country_study_counts):,}.")
    add("- Dependence can arise within country, survey program, fieldwork period, region, mode, interviewer, and questionnaire design.")
    countries_by_study: dict[str, set[str]] = {
        study: {
            country
            for country, observed_study in profile.country_study_counts
            if observed_study == study
        }
        for study in STUDY_LABELS
    }
    countries_in_both = sorted(set.intersection(*countries_by_study.values()))
    add(
        f"- Countries represented by both EVS and WVS ({len(countries_in_both)}): "
        f"{', '.join(countries_in_both)}. These are separate samples, not repeated observations of the same people."
    )
    add("")
    add("### Source studies")
    add("")
    add("| Study code | Study | Respondents | Share |")
    add("|---:|---|---:|---:|")
    for study in sorted(profile.study_counts, key=numeric_sort_key):
        count = profile.study_counts[study]
        add(f"| {study} | {STUDY_LABELS.get(study, 'Unknown')} | {count:,} | {percentage(count, n)} |")
    add("")
    add("### Survey years")
    add("")
    add("| Year | Respondents | Share |")
    add("|---:|---:|---:|")
    for year in sorted(profile.year_counts, key=numeric_sort_key):
        count = profile.year_counts[year]
        add(f"| {year} | {count:,} | {percentage(count, n)} |")
    add("")
    add("### Modes of data collection")
    add("")
    add("| Mode code | Mode | Respondents | Share |")
    add("|---:|---|---:|---:|")
    for mode in sorted(profile.mode_counts, key=numeric_sort_key):
        count = profile.mode_counts[mode]
        add(
            f"| {mode} | {MODE_LABELS.get(mode, 'Unknown')} | {count:,} | "
            f"{percentage(count, n)} |"
        )
    add("")
    min_country, min_country_n = min(profile.country_counts.items(), key=lambda item: item[1])
    max_country, max_country_n = max(profile.country_counts.items(), key=lambda item: item[1])
    add(f"Country sample sizes range from {min_country_n:,} ({min_country}) to {max_country_n:,} ({max_country}).")
    add("")

    add("## 3. Candidate target and predictors")
    add("")
    add("| Variable | Meaning | Statistical type / support | Valid | Missing |")
    add("|---|---|---|---:|---:|")
    for variable, definition in KEY_VARIABLES.items():
        counts = profile.key_counts[variable]
        valid = sum(valid_counter(variable, counts).values())
        missing = sum(counts[code] for code in MISSING_CODES) + counts[""]
        support = definition.statistical_type
        if definition.note:
            support += f"; {definition.note}"
        add(
            f"| `{variable}` | {definition.label} | {support} | "
            f"{valid:,} ({percentage(valid, n)}) | {missing:,} ({percentage(missing, n)}) |"
        )
    add("")
    add(
        "`A170` is a plausible response `Y`. The other listed variables are candidate predictors, "
        "not a final feature set. Associations in this observational survey must not be interpreted as causal effects."
    )
    add(
        "The raw model representation is mostly integer-coded survey categories plus identifiers, strings, "
        "and continuous weights. Category numbers must not automatically be treated as meaningful Euclidean "
        "distances; nominal variables need an explicit encoding strategy, while ordinal variables may retain "
        "their order under a suitable model."
    )
    add("")

    target_valid = valid_counter("A170", profile.key_counts["A170"])
    target_n = sum(target_valid.values())
    target_mean = sum(float(value) * count for value, count in target_valid.items()) / target_n
    target_median = median_from_counts(target_valid)
    target_high = sum(count for value, count in target_valid.items() if int(value) >= 7)
    add("### Candidate target distribution: `A170`")
    add("")
    add(
        f"Valid mean: {target_mean:.3f}; valid median: {target_median:g}; "
        f"responses 7-10: {target_high:,} ({percentage(target_high, target_n)} of valid responses)."
    )
    add("")
    add("| Life satisfaction | Count | Share of valid responses |")
    add("|---:|---:|---:|")
    for value in sorted(target_valid, key=numeric_sort_key):
        count = target_valid[value]
        add(f"| {value} | {count:,} | {percentage(count, target_n)} |")
    add("")

    add("## 4. Missingness")
    add("")
    add(
        f"Blank CSV cells: {profile.blank_cells:,}. The dataset instead uses the five official negative "
        "missing-value codes. They must be converted to missing values or handled explicitly before modelling, "
        "but they should not be globally replaced in the immutable raw file."
    )
    add("")
    add("| Code | Meaning | Cells in full CSV | Share of all cells |")
    add("|---:|---|---:|---:|")
    for code, meaning in MISSING_CODES.items():
        count = profile.missing_counts[code]
        add(f"| {code} | {meaning} | {count:,} | {percentage(count, total_cells)} |")
    add("")
    add("### Missing-code detail for important variables")
    add("")
    add("| Variable | -1 | -2 | -3 | -4 | -5 |")
    add("|---|---:|---:|---:|---:|---:|")
    for variable in KEY_VARIABLES:
        counts = profile.key_counts[variable]
        add(
            f"| `{variable}` | {counts['-1']:,} | {counts['-2']:,} | {counts['-3']:,} | "
            f"{counts['-4']:,} | {counts['-5']:,} |"
        )
    add("")
    add("Reasoned mechanism hypotheses:")
    add("")
    add("- Missingness is unlikely to be globally MCAR.")
    add("- `-4` is structural and determined by survey source, country, or questionnaire design.")
    add("- MAR is plausible after conditioning on country, study, mode, year, and demographics.")
    add("- Refusal or uncertainty for sensitive questions such as income may be MNAR.")
    add("- Keep the five reasons distinguishable during data preparation; do not impute at this stage.")
    add("")

    add("### Source-specific income variables")
    add("")
    add("| Study | Variable | Valid | -1 | -2 | -3 | -4 | -5 |")
    add("|---|---|---:|---:|---:|---:|---:|---:|")
    for study in sorted(STUDY_LABELS, key=numeric_sort_key):
        for variable in ("X047_WVS7", "X047E_EVS5"):
            counts = profile.income_by_study[(study, variable)]
            add(
                f"| {STUDY_LABELS[study]} | `{variable}` | {counts['valid']:,} | {counts['-1']:,} | "
                f"{counts['-2']:,} | {counts['-3']:,} | {counts['-4']:,} | {counts['-5']:,} |"
            )
    add("")
    add(
        "These income variables are source-specific and measure related but not identical constructs. "
        "Do not combine them solely because both use codes 1-10."
    )
    add("")

    add("## 5. Data quality, censoring, and weights")
    add("")
    add("| Check | Result |")
    add("|---|---:|")
    for variable in KEY_VARIABLES:
        invalid = invalid_count(variable, profile.key_counts[variable])
        add(f"| `{variable}` values outside documented support (excluding missing codes) | {invalid:,} |")
    for variable, top_code in TOP_CODED_VARIABLES.items():
        count = profile.key_counts[variable][top_code]
        add(f"| `{variable}` observations in top-coded category `{top_code}` | {count:,} ({percentage(count, n)}) |")
    add("")
    add(
        "The top-coded values are censored categories, not exact high values or automatic errors. "
        "Potentially influential survey weights should be inspected rather than discarded as outliers."
    )
    add("")
    add("### Weight variables")
    add("")
    add("| Weight | Non-missing | Minimum | Mean | Maximum | Intended role |")
    add("|---|---:|---:|---:|---:|---|")
    weight_roles = {
        "gwght": "Adjust sample demographics toward the target population.",
        "pwght": "Population-size weighting when pooling countries.",
        "wght_eq1000": "Give each country sample an effective size of 1,000.",
    }
    for variable in WEIGHT_VARIABLES:
        summary = profile.weight_summaries[variable]
        add(
            f"| `{variable}` | {summary.count:,} | {summary.minimum:.6g} | {summary.mean:.6g} | "
            f"{summary.maximum:.6g} | {weight_roles[variable]} |"
        )
    add("")

    add("## 6. Sample, bias, leakage, and distribution shift")
    add("")
    add("- Target population in the documentation: generally adults living in private households; EVS uses age 18+, while WVS can include ages 16/17 where the voting age is lower.")
    add("- Sampling: country-level single-stage or multistage probability samples. Nonresponse and exclusion of people outside private households can still create selection bias.")
    add("- Survey weights adjust selected observed margins, but they do not remove every form of selection or measurement bias.")
    add("- Random respondent-level train/test splitting shares countries and survey contexts between sets and can overstate transfer to new countries or periods.")
    add("- For new-country generalisation, hold out complete countries or country-study groups. For future-period generalisation, use a temporal split where possible.")
    add("- Expected shifts include country composition, fieldwork year, survey mode, translation, political/economic conditions, and the COVID-19 period.")
    add("- Administrative fields, identifiers, fieldwork dates, and source-specific variables can encode country/study context and must be reviewed for leakage before modelling.")
    add("")

    add("## 7. Measurement, signal, noise, and first modelling intuition")
    add("")
    add("- Life satisfaction, happiness, health, trust, freedom/control, and income are self-reported and may contain recall error, social-desirability bias, cultural response styles, and mode/translation effects.")
    add("- Potentially important omitted variables include current life events, mental health detail, wealth, personality, local prices, and other country-time conditions.")
    add("- Plausible signal: subjective health, happiness, perceived control, employment, education, income, age, household composition, and country context.")
    add("- Plausible irreducible noise: temporary mood, individual circumstances not measured in the survey, response-scale interpretation, and local events.")
    add("- Closely related subjective predictors such as happiness and perceived control may predict `A170` strongly, but contemporaneous association is not causation.")
    add("- A reasonable first approach is an ordinal or carefully justified numeric model with country effects and country-level stability checks; compare it with a simple baseline.")
    add("- The main anticipated difficulty is cross-country and cross-survey heterogeneity, not raw computational scale.")
    add("")

    add("## 8. Report figure shortlist")
    add("")
    add("Use only figures that support a written conclusion. Strong candidates are:")
    add("")
    add("1. Distribution of `A170`.")
    add("2. Compact missingness plot for the final target and predictors, preserving missing-code reasons.")
    add("3. Country sample sizes or valid-target coverage by country.")
    add("4. Fieldwork-year coverage, especially the uneven 2017-2023 composition.")
    add("")
    add("Do not use the output as a causal analysis or as a substitute for citing the official documentation.")
    add("")

    add("## 9. Assignment submission checklist")
    add("")
    add("- Submit a PDF in the most condensed form possible.")
    add("- Maximum length: two pages of text; figures may be added only when they answer a report question.")
    add("- Include the dataset source/link clearly enough that the data can be found again.")
    add("- Verify the licence/terms and exact deadline from the official access page and Moodle.")
    add("- The deadline is before Lecture 3 (Develop block), with the exact date on Moodle.")
    add("")
    return "\n".join(lines)


def main() -> int:
    args = parse_args()
    try:
        csv_path = args.csv.expanduser().resolve()
        profile = profile_csv(csv_path)
        report = render_report(csv_path, profile)
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
