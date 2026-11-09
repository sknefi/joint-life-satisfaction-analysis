# Semester project: EVS life satisfaction analysis

This repository supports a university Data Science project using the Joint EVS/WVS 2017-2022 Dataset, Version 5.0.0. Work is organized into four course stages: Define, Develop, Assure, and Operate. Define and Develop now include implemented analysis and PDF reports. Assure and Operate remain future stages.

The project uses the EVS portion of the joint file, with fieldwork during 2017-2021, as its primary analytical sample. The current research question is:

> Which demographic, socioeconomic, and social characteristics are associated with life satisfaction among EVS respondents, and how stable are these relationships across participating countries?

The response variable is `A170`, satisfaction with life, on the ordinal 1-10 scale. EVS is selected using `study == 1`; the joint raw CSV remains unchanged. The EVS subset contains 59,438 respondents from 36 countries. Develop compares predictive models and estimates weighted descriptive associations. It does not identify causal effects.

## Quickstart: use the released model without the survey data

Use Python **3.12** for the tested v0.1.0 environment. Clone this repository and
run the following from its root:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-model-lock.txt
python -m pip install --no-deps .
evs-predict --input examples/respondents.csv --output predictions.csv
python -m unittest discover -s tests -p 'test_*.py'
```

`examples/respondents.csv` contains invented profiles. The package and example
do not require raw survey data. `notebooks/quickstart.ipynb` provides an executed
walkthrough; install `.[dev]` to run it interactively. If working outside the
repository root, pass `--model /path/to/models/evs_v0_1_0.joblib`.

The wheel installs the code; the versioned model and its metadata are separate
files in `models/`. Their exact fitted dependency versions are recorded in
`requirements-model-lock.txt`. `requirements-lock.txt` additionally freezes the
full report/notebook authoring environment. No service is hosted or deployed.

### Prediction contract

Required CSV headers are:

```text
X001,X003,X025R,X028,X047E_EVS5,A009,A165,A173,cntry_AN
```

Use the official codebook: sex 1-2, age 18-82, education 1-3, employment 1-8,
income decile 1-10, health 1-5, trust 1-2, control 1-10, and the country label.
Age 82 means **82 or older**. Blank values and documented codes -1 through -5
are handled as missing; country is mandatory. The command rejects unknown
countries, out-of-support/fractional categories, non-numeric codes, extra fields,
and target/administrative fields. It validates the entire file before atomically
replacing the requested output, and refuses to overwrite the input file.

Output columns are `predicted_score` (median of the predicted distribution),
`probability_high_7_10`, and `p_1` through `p_10`. A probability distribution is
not an individual confidence interval. Changing employment or income in a
profile does not estimate the causal effect of changing that circumstance.

Supported historical country contexts are AL, AM, AZ, BA, BG, BY, CH, CZ, DE, DK,
EE, ES, FI, GE, HR, HU, IS, IT, LV, ME, NL, NO, PL, PT, RO, RU, SE, SI, SK, UA.
AT, FR, GB, LT, MK and RS are held out for the future country-transfer test.
Later periods, new countries and different questionnaires require validation.

## Develop results and reproduction

The frozen choice is histogram gradient boosting, trained on **34,740** cases.
Five-fold **training-only** CV MAEs are baseline **1.565**, ordinal **1.255**,
random forest **1.250**, and boosting **1.225**. The 5,007-case production
validation gives boosting MAE **1.213** after selection was frozen. These are
not final Assure test results: 10,079 same-country and 9,296 held-out-country
prediction-test cases remain reserved.

Primary predictors exclude happiness. Adding that near-proxy gives CV MAE
1.102; using only demographic/economic inputs gives 1.447 with the frozen
selected-family configuration. This sensitivity is not separately retuned.

Weighted high-satisfaction proportions are 72.51% unweighted, 70.99% with
equal-country-size scaling, and 68.60% with population-size scaling. The
high-minus-low income and paid-work-minus-unemployed gaps are **associations**.
Intervals use an approximate within-country respondent bootstrap, not a full
complex-survey design. See the reports and model card for limitations.

For complete reproduction, obtain the source files as described in
[`data/README.md`](data/README.md), then install the full environment:

```bash
python -m pip install -r requirements-lock.txt
python -m pip install --no-deps -e .
make data
make train
make inference
make verify-production
make develop-reports
make package
```

`make setup` performs the full installation. You can select another interpreter
with `make PYTHON=/path/to/venv/bin/python ...`; the default is `.venv/bin/python`.
Training caps numerical threads and uses four independent fold workers.

- `02_develop/report/`: generated readable report sources.
- `02_develop/output/`: the three reviewed PDFs, included in Git.
- `02_develop/results/`: aggregate trials, coefficients, diagnostics and inference.
- `02_develop/local/`: ignored respondent split IDs, fold predictions and checkpoints.
- `models/`: the selected model, metadata and model card.

Training checkpoints are keyed by source, code, versions and configuration.
An unchanged rerun reuses fold results. If code/source identity changes, move
the existing `02_develop/local/` aside before starting a fresh run; the command
refuses to silently mix incompatible checkpoints. Inferential descriptions use
all 36 countries as a separate pre-specified pipeline, never as a final model
comparison. The primary prediction target is an unweighted EVS-style respondent;
survey weights are used in the separate population-inference analysis.

The custom ordinal estimator implements the all-threshold logistic objective
with analytic gradients and ordered cutpoint constraints, retaining optimizer
diagnostics. It is not categorical ordered-logit maximum likelihood. The
gradient is checked numerically in the tests. All encodings and imputation are
fit inside each validation fold. Grouped CV is a secondary diagnostic, not a
nested estimate after hyperparameter selection.

GitHub Actions runs the installed package tests on synthetic fixtures and the
released example; it does not download the survey or retrain on private data.
Tag `v0.1.0` identifies the first reusable Develop version. The code is installable
with pip from the repository; it is not published to PyPI.

## Data and documentation

| File | Description | Original source |
|---|---|---|
| `data/raw/evs_wvs_dataset.csv` | EVS/WVS Joint v5.0 CSV dataset | [World Values Survey: Joint EVS/WVS 2017-2022](https://www.worldvaluessurvey.org/WVSEVSjoint2017.jsp) |
| `docs/ZA7505_cdb.pdf` | EVS/WVS Joint v5.0 variable report/codebook | [World Values Survey: Joint EVS/WVS 2017-2022](https://www.worldvaluessurvey.org/WVSEVSjoint2017.jsp) |
| `01_define/subject/` | Problem Definition Report assignment briefs (Parts I and II) | [VSE Moodle](https://moodle.vse.cz/mod/folder/view.php?id=857464) |
| `02_develop/subject/` | Model Development Report assignment briefs (Parts I-III) | [VSE Moodle](https://moodle.vse.cz/mod/folder/view.php?id=857464) |

The accompanying `info.txt` files identify the downloaded source files and their origins.

Treat everything under `data/raw/` as immutable source data. Analysis code must read the CSV without modifying or replacing it. In particular, the official negative missing-value codes must not be overwritten in the raw file.

The joint CSV remains the only source of truth. `make data` creates an EVS-only Parquet file as a reproducible, disposable analytical artifact rather than an independently maintained dataset. The profile reports the original joint CSV size (104.3 MiB), the CSV-equivalent size of its EVS rows (40.4 MiB), and the actual generated Parquet size (currently 3.8 MiB with Zstandard compression).

## Project structure

```text
.
├── 01_define
│   ├── subject                   # Problem Definition briefs
│   ├── report                    # LaTeX sources and generated EVS profile
│   └── output                    # Rendered PDFs; kept locally
├── 02_develop
│   ├── subject                   # Model Development briefs
│   ├── report
│   └── output
├── 03_assure
│   ├── subject
│   ├── report
│   └── output
├── 04_operate
│   ├── subject
│   ├── report
│   └── output
├── Makefile
├── README.md
├── requirements.txt
├── data
│   ├── processed
│   │   └── evs_v5_0.parquet          # Generated by `make data`; not committed
│   └── raw
│       ├── evs_wvs_dataset.csv
│       └── info.txt
├── docs
│   ├── ZA7505_cdb.pdf           # Shared dataset codebook
│   └── info.txt
├── scripts
│   ├── build_evs_parquet.py
│   └── profile_dataset.py
├── src
│   └── evs_profile
│       ├── __init__.py
│       ├── config.py
│       ├── dataset.py
│       ├── reader.py
│       ├── report.py
│       └── statistics.py
└── tests
    ├── test_dataset.py
    ├── test_reader.py
    └── test_statistics.py
```

`scripts/profile_dataset.py` is only the command-line entry point. The implementation is separated by responsibility:

- `config.py` contains documented codes, country names, and variable definitions;
- `dataset.py` builds and validates the reproducible EVS Parquet artifact;
- `reader.py` streams the immutable CSV and applies the EVS/WVS filter;
- `statistics.py` contains reusable calculations and validation helpers;
- `report.py` renders the Markdown profile;
- `tests/` verifies study filtering and the core calculations.

## Setup

Create the local virtual environment:

```bash
make setup
```

The setup installs the pinned full environment and this local package. The `.venv/` directory is local and excluded from version control. For prediction and tests only, the smaller quickstart installation above is sufficient.

Activating the environment is optional when using `make`. To run Python commands directly, activate it with:

```bash
source .venv/bin/activate
```

## Generate the data profile

Build the reproducible EVS Parquet dataset:

```bash
make data
```

This reads the immutable joint CSV, selects `study == 1`, drops the five `_WVS7` columns, validates 59,438 rows and 226 columns, preserves the documented negative missing codes, and writes:

```text
data/processed/evs_v5_0.parquet
data/processed/evs_v5_0.metadata.json
```

Both files are generated artifacts excluded from Git. The metadata manifest and Parquet schema contain the source CSV SHA-256 hash and transformation details.

Print the EVS-focused report-ready profile in the terminal:

```bash
make
```

The explicit equivalent is:

```bash
make profile
```

Print the EVS profile and save it to `01_define/report/data_profile_evs.md`:

```bash
make report
```

Other useful commands are:

```bash
make profile-all  # Profile the complete joint EVS/WVS dataset for comparison
make data         # Rebuild the validated EVS Parquet dataset
make test         # Run unit tests
make check        # Compile all modules and run unit tests
make help         # List all Makefile commands
```

The Python script can also be run directly:

```bash
python scripts/profile_dataset.py --study EVS
python scripts/profile_dataset.py --study EVS --output 01_define/report/data_profile_evs.md
python scripts/profile_dataset.py --study all
```

`EVS` is the default value of `--study`, so it may be omitted. `WVS` is also accepted when a WVS-only comparison is needed.

## Profile contents

The generated profile covers the information needed for the assignment, including:

- source and EVS-subset sizes (`n`, `p`, on-disk MiB, and memory baseline) and computational profile;
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
