# Semester project: Joint EVS/WVS data understanding

This repository supports the data-understanding stage of a university Data Science project using the Joint EVS/WVS 2017-2022 Dataset, Version 5.0.0.

The current candidate research question is:

> Which demographic, socioeconomic, and social characteristics are associated with life satisfaction, and how stable are these relationships across countries?

The likely response variable is `A170`, satisfaction with life. The project currently focuses on understanding the data rather than fitting a machine-learning model or making causal claims.

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
└── scripts
    └── profile_dataset.py
```

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

Print the complete report-ready profile in the terminal:

```bash
make
```

The explicit equivalent is:

```bash
make profile
```

Print the profile and save it to `reports/data_profile.md`:

```bash
make report
```

Other useful commands are:

```bash
make check  # Validate the Python profiler
make help   # List all Makefile commands
```

The Python script can also be run directly:

```bash
python scripts/profile_dataset.py
python scripts/profile_dataset.py --output reports/data_profile.md
```

## Profile contents

The generated profile covers the information needed for the assignment, including:

- dataset size (`n` and `p`), file size, and computational profile;
- respondent, country, survey, year, and collection-mode structure;
- candidate target and predictor definitions and statistical types;
- the distribution of `A170`;
- official missing codes and variable-level missingness;
- source-specific EVS5/WVS7 variables, especially the two income measures;
- duplicate-ID, documented-support, and top-coding checks;
- survey-weight summaries;
- dependence, leakage, selection-bias, and distribution-shift considerations;
- measurement error, expected signal and noise, and initial modelling intuition;
- assignment constraints and a shortlist of potentially useful figures.

The generated text is a reproducible starting point for the report. Claims about survey design, variable meanings, and coding should still cite the official codebook.
