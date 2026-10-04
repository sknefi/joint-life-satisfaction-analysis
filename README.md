# Semester project: Joint EVS/WVS data understanding

This repository supports the data-understanding stage of a university Data Science project using the Joint EVS/WVS 2017-2022 Dataset, Version 5.0.0.

The project uses the EVS 2017 portion of the joint file as its primary analytical sample. The current research question is:

> Which demographic, socioeconomic, and social characteristics are associated with life satisfaction among respondents in EVS 2017, and how stable are these relationships across participating countries?

The likely response variable is `A170`, satisfaction with life. EVS is selected in analysis code using `study == 1`; the joint raw CSV remains unchanged. The EVS subset contains 59,438 respondents from 36 participating countries. The project currently focuses on understanding the data rather than fitting a machine-learning model or making causal claims.

## Data and documentation

| File | Description | Original source |
|---|---|---|
| `data/raw/evs_wvs_dataset.csv` | EVS/WVS Joint v5.0 CSV dataset | [World Values Survey: Joint EVS/WVS 2017-2022](https://www.worldvaluessurvey.org/WVSEVSjoint2017.jsp) |
| `docs/ZA7505_cdb.pdf` | EVS/WVS Joint v5.0 variable report/codebook | [World Values Survey: Joint EVS/WVS 2017-2022](https://www.worldvaluessurvey.org/WVSEVSjoint2017.jsp) |
| `docs/subject/problem_definition_report_part1_data.pdf` | University assignment: Problem Definition Report, Part I - Data | [VSE Moodle](https://moodle.vse.cz/mod/folder/view.php?id=857464) |

The accompanying `info.txt` files record the source and original description of each downloaded artifact.

Treat everything under `data/raw/` as immutable source data. Analysis code must read the CSV without modifying or replacing it. In particular, the official negative missing-value codes must not be overwritten in the raw file.

## Project structure

```text
.
├── Makefile
├── README.md
├── requirements.txt
├── data
│   └── raw
│       ├── evs_wvs_dataset.csv
│       └── info.txt
├── docs
│   ├── ZA7505_cdb.pdf
│   ├── info.txt
│   └── subject
│       ├── info.txt
│       └── problem_definition_report_part1_data.pdf
├── scripts
│   └── profile_dataset.py
├── src
│   └── evs_profile
│       ├── __init__.py
│       ├── config.py
│       ├── reader.py
│       ├── report.py
│       └── statistics.py
└── tests
    ├── test_reader.py
    └── test_statistics.py
```

`scripts/profile_dataset.py` is only the command-line entry point. The implementation is separated by responsibility:

- `config.py` contains documented codes, country names, and variable definitions;
- `reader.py` streams the immutable CSV and applies the EVS/WVS filter;
- `statistics.py` contains reusable calculations and validation helpers;
- `report.py` renders the Markdown profile;
- `tests/` verifies study filtering and the core calculations.

## Setup

Create the local virtual environment:

```bash
make setup
```

The profiler uses only the Python standard library, so no third-party packages are currently required. The `.venv/` directory is local and excluded from version control.

Activating the environment is optional when using `make`. To run Python commands directly, activate it with:

```bash
source .venv/bin/activate
```

## Generate the data profile

Print the EVS-focused report-ready profile in the terminal:

```bash
make
```

The explicit equivalent is:

```bash
make profile
```

Print the EVS profile and save it to `reports/data_profile_evs.md`:

```bash
make report
```

Other useful commands are:

```bash
make profile-all  # Profile the complete joint EVS/WVS dataset for comparison
make test         # Run unit tests
make check        # Compile all modules and run unit tests
make help         # List all Makefile commands
```

The Python script can also be run directly:

```bash
python scripts/profile_dataset.py --study EVS
python scripts/profile_dataset.py --study EVS --output reports/data_profile_evs.md
python scripts/profile_dataset.py --study all
```

`EVS` is the default value of `--study`, so it may be omitted. `WVS` is also accepted when a WVS-only comparison is needed.

## Profile contents

The generated profile covers the information needed for the assignment, including:

- dataset size (`n` and `p`), file size, and computational profile;
- respondent, country, survey, year, and collection-mode structure;
- candidate target and predictor definitions and statistical types;
- the distribution of `A170`;
- official missing codes and variable-level missingness;
- source-specific EVS5/WVS7 variables, including the use of `X047E_EVS5` and exclusion of `X047_WVS7` in the EVS analysis;
- duplicate-ID, documented-support, and top-coding checks;
- survey-weight summaries;
- dependence, leakage, selection-bias, and distribution-shift considerations;
- measurement error, expected signal and noise, and initial modelling intuition;
- assignment constraints and a shortlist of potentially useful figures.

The generated text is a reproducible starting point for the report. Claims about survey design, variable meanings, and coding should still cite the official codebook.
