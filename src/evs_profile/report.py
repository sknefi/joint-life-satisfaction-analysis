"""Markdown report rendering for EVS/WVS profiles."""

from __future__ import annotations

from pathlib import Path

from .config import (
    COUNTRY_NAMES,
    KEY_VARIABLES,
    MISSING_CODES,
    MODE_LABELS,
    STUDY_LABELS,
    TOP_CODED_VARIABLES,
    WEIGHT_VARIABLES,
)
from .reader import Profile
from .statistics import (
    human_bytes,
    invalid_count,
    median_from_counts,
    numeric_sort_key,
    percentage,
    valid_counter,
    variable_family_counts,
)


def render_report(
    csv_path: Path,
    profile: Profile,
    study_option: str = "EVS",
    parquet_path: Path | None = None,
) -> str:
    """Render a complete report-ready Markdown summary."""

    n = profile.row_count
    p = len(profile.columns)
    available_columns = [
        column for column in profile.columns if profile.column_valid_counts[column] > 0
    ]
    unavailable_columns = [
        column for column in profile.columns if profile.column_valid_counts[column] == 0
    ]
    active_key_variables = list(KEY_VARIABLES)
    if study_option == "EVS":
        active_key_variables.remove("X047_WVS7")
        scope_title = "EVS 2017 analytical subset"
        scope_description = "EVS respondents only (`study = 1`)"
    elif study_option == "WVS":
        active_key_variables.remove("X047E_EVS5")
        scope_title = "WVS7 analytical subset"
        scope_description = "WVS respondents only (`study = 2`)"
    else:
        scope_title = "Joint EVS/WVS 2017-2022 dataset"
        scope_description = "complete joint dataset (EVS and WVS)"

    raw_size = csv_path.stat().st_size
    dense_numeric_bytes = n * p * 8
    total_cells = n * p
    families = variable_family_counts(profile.columns)
    source_specific_evs = sum(column.endswith("_EVS5") for column in profile.columns)
    source_specific_wvs = sum(column.endswith("_WVS7") for column in profile.columns)

    lines: list[str] = []
    add = lines.append
    add(f"# {scope_title}: data profile")
    add("")
    add(f"- CSV inspected: `{csv_path.resolve()}`")
    add("- Source dataset: Joint EVS/WVS 2017-2022, Version 5.0.0")
    add(f"- Analysis scope: {scope_description}")
    add("- The source CSV remains unchanged; filtering occurs only while this profile is calculated.")
    add("- Producers: European Values Study and World Values Survey")
    add("- GESIS DOI: <https://doi.org/10.4232/1.14320>")
    add("- WVSA DOI: <https://doi.org/10.14281/18241.26>")
    add("- Licence/terms: not stated in the supplied Variable Report; verify the official access page before submission.")
    add("")

    add("## 1. Size and computational profile")
    add("")
    add("| Quantity | Result |")
    add("|---|---:|")
    add(f"| Rows in the source joint CSV | {profile.source_row_count:,} |")
    add(f"| Rows / observations in this analytical scope (`n`) | {n:,} |")
    add(f"| Selected share of source respondents | {percentage(n, profile.source_row_count)} |")
    add(f"| Delivered columns in the joint CSV (`p_raw`) | {p:,} |")
    add(f"| Columns with at least one non-missing value in this scope | {len(available_columns):,} |")
    add(f"| Structurally unavailable columns in this scope | {len(unavailable_columns):,} |")
    add(f"| Maximum available non-target columns if `Y = A170` | {len(available_columns) - 1:,} |")
    add(f"| `n / p_raw` | {n / p:,.1f} |")
    add("| Source files / tables | 1 CSV file / 1 table |")
    add(f"| Source joint CSV size on disk | {raw_size:,} bytes ({human_bytes(raw_size)}) |")
    if profile.selected_csv_bytes is not None:
        add(
            f"| Selected rows' CSV-equivalent size | {profile.selected_csv_bytes:,} bytes "
            f"({human_bytes(profile.selected_csv_bytes)}), calculated without creating a second file |"
        )
    if study_option == "EVS":
        if parquet_path is not None and parquet_path.is_file():
            parquet_bytes = parquet_path.stat().st_size
            add(
                f"| Derived EVS Parquet size on disk (Zstandard) | {parquet_bytes:,} bytes "
                f"({human_bytes(parquet_bytes)}) |"
            )
            if profile.selected_csv_bytes:
                reduction = 100 * (1 - parquet_bytes / profile.selected_csv_bytes)
                ratio = profile.selected_csv_bytes / parquet_bytes
                add(
                    f"| Parquet reduction versus EVS CSV-equivalent | "
                    f"{reduction:.2f}% smaller ({ratio:.1f}x) |"
                )
        else:
            add("| Derived EVS Parquet size on disk | Not generated; run `make data` |")
    add(f"| Dense 8-byte matrix baseline | {human_bytes(dense_numeric_bytes)} plus software/string overhead |")
    add("")
    add(
        "Interpretation: the file fits comfortably in ordinary laptop memory, and this script can also "
        "profile it as a stream. The subset is much larger in `n` than in `p`; computational size is "
        "not the main modelling difficulty. The final predictor count will be lower before encoding "
        "because IDs, protocol variables, weights, and the target are not ordinary predictors."
    )
    if study_option != "all" and profile.selected_csv_bytes is not None:
        add(
            f"The source file remains {human_bytes(raw_size)} on disk because the subset is filtered at "
            f"runtime. If the selected rows and header were copied unchanged into a separate CSV, that "
            f"file would be {human_bytes(profile.selected_csv_bytes)}; no such duplicate is required."
        )
    if unavailable_columns:
        add(
            "Columns that are wholly unavailable in this scope: "
            + ", ".join(f"`{column}`" for column in unavailable_columns)
            + "."
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
    included_countries = [
        f"{COUNTRY_NAMES.get(code, code)} ({code})" for code in sorted(profile.country_counts)
    ]
    add("- Included countries: " + ", ".join(included_countries) + ".")
    if len(profile.study_counts) > 1:
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
    for variable in active_key_variables:
        definition = KEY_VARIABLES[variable]
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
    add("| Code | Meaning | Cells in selected rows | Share of selected cells |")
    add("|---:|---|---:|---:|")
    for code, meaning in MISSING_CODES.items():
        count = profile.missing_counts[code]
        add(f"| {code} | {meaning} | {count:,} | {percentage(count, total_cells)} |")
    add("")
    add("### Missing-code detail for important variables")
    add("")
    add("| Variable | -1 | -2 | -3 | -4 | -5 |")
    add("|---|---:|---:|---:|---:|---:|")
    for variable in active_key_variables:
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
    for study in sorted(profile.study_counts, key=numeric_sort_key):
        for variable in ("X047_WVS7", "X047E_EVS5"):
            counts = profile.income_by_study[(study, variable)]
            add(
                f"| {STUDY_LABELS[study]} | `{variable}` | {counts['valid']:,} | {counts['-1']:,} | "
                f"{counts['-2']:,} | {counts['-3']:,} | {counts['-4']:,} | {counts['-5']:,} |"
            )
    add("")
    if study_option == "EVS":
        add("Use `X047E_EVS5` for the EVS analysis and exclude the unavailable `X047_WVS7` field.")
    elif study_option == "WVS":
        add("Use `X047_WVS7` for the WVS analysis and exclude the unavailable `X047E_EVS5` field.")
    else:
        add(
            "These income variables are source-specific and measure related but not identical constructs. "
            "Do not combine them solely because both use codes 1-10."
        )
    add("")

    add("## 5. Data quality, censoring, and weights")
    add("")
    add("| Check | Result |")
    add("|---|---:|")
    for variable in active_key_variables:
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
    if study_option == "EVS":
        add("- EVS target population: people aged 18 or older, with no upper age limit, residing in private households in the surveyed country.")
    elif study_option == "WVS":
        add("- WVS target population: generally people aged 18 or older in private households, with ages 16/17 permitted where the voting age is lower.")
    else:
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
    difficulty = "cross-country and cross-mode heterogeneity"
    if study_option == "all":
        difficulty = "cross-country, cross-mode, and cross-survey heterogeneity"
    add(f"- The main anticipated difficulty is {difficulty}, not raw computational scale.")
    add("")

    add("## 8. Report figure shortlist")
    add("")
    add("Use only figures that support a written conclusion. Strong candidates are:")
    add("")
    add("1. Distribution of `A170`.")
    add("2. Compact missingness plot for the final target and predictors, preserving missing-code reasons.")
    add("3. Country sample sizes or valid-target coverage by country.")
    years = sorted(profile.year_counts, key=numeric_sort_key)
    add(f"4. Fieldwork-year coverage, especially the uneven {years[0]}-{years[-1]} composition.")
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
