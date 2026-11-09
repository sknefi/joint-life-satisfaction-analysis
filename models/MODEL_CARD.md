# EVS life-satisfaction model v0.1.0

## Purpose and scope

Research demonstration: predict the ordinal A170 response (1-10) for a new
EVS-style adult respondent after the other required survey answers are available.
The context is the 2017-2021 EVS wave, not current well-being monitoring.
The frozen bundle is histogram gradient boosting with its fitted preprocessing.
It was selected before the separate production validation was evaluated.

This model does not estimate causal effects or recommend interventions. Changing
employment in the input does not answer what would happen if someone obtained a
job. Imputation for people who did not answer A170 would require additional
validation of the missing-target population; performance on observed targets
does not prove that missing targets are exchangeable.

## Data and inputs

- Source: Joint EVS/WVS 2017-2022, ZA7505 v5.0.0, EVS `study == 1`.
- Source subset: 59,438 respondents / 36 countries; valid A170: 59,122.
- Predictive training: 34,740 cases / 30 countries, unweighted.
- Inputs: X001, X003, X025R, X028, X047E_EVS5, A009, A165, A173, cntry_AN.
- Happiness A008 is excluded from the primary predictor set.
- Year, mode, IDs and weights are not primary model inputs.
- Age is top-coded at 82; other inputs use explicit categories with missingness.
- Training-only age median and scale parameters are stored in the artifact.

Supported countries are listed in the companion metadata and README. AT, FR,
GB, LT, MK and RS were held out entirely for later testing. Public prediction
refuses unsupported countries; group CV diagnoses transfer using zeroed unknown
country indicators internally.

## Validation

Five-fold within-country training CV: baseline MAE 1.565, ordinal 1.255,
forest 1.250, boosting 1.225. The selected boosting model's log loss is 1.715,
normalized RPS 0.0963, and high-satisfaction Brier score 0.1451.

Secondary five-fold country-group CV MAE is 1.266. It is not nested CV: its
hyperparameters were chosen using within-country CV across the training sample.
It is therefore a diagnostic rather than an untouched transfer-test estimate.

Independent production validation (5,007 cases): MAE 1.213, log loss 1.711,
RPS 0.0963. It did not affect the choice, hyperparameters or model fitting.
The final same-country test (10,079 cases) and six-country test (9,296 cases)
remain reserved for Assure. No final prediction-test scores are published.

Probability reliability is saved in `production_validation.json` and
`calibration_cv.json`. It is imperfect, particularly for sparsely populated
probability bins. The package reports category probabilities, not calibrated
individual prediction intervals; no nominal interval coverage is promised.

## Limitations and monitoring

Self-reported life satisfaction is noisy and culturally interpreted. Country,
translation and survey-mode effects may partly drive prediction. Income is
missing for 14.70% of the source subset and may be MNAR; handling a missing code
does not eliminate missingness bias. The model cannot distinguish ages above 82.
It excludes people outside private households and may perform poorly in rare
subgroups, new countries, later crises or different questionnaires.

Country and demographic CV error aggregates are available for inspection; no
fairness guarantee or causal interpretation follows from a good pooled score.
Monitor missingness, feature/category drift and labelled error by country when
new data become available. Validate before expanding scope; retrain and release
a new version only after documenting the new evaluation.

## Reproduction

Use the exact runtime versions in `requirements-model-lock.txt` and the model
checksum and provenance in `evs_v0_1_0.metadata.json`. The metadata's
`source_sha256` hashes the input EVS Parquet; that Parquet's schema records the
original immutable CSV hash. The source dataset remains the original joint CSV.

The repository includes synthetic inputs, an executed notebook, 17 automated
tests, source code, aggregate training diagnostics and three reports. Raw survey
records, respondent split IDs and fold probability checkpoints are excluded from
distribution. The binary model is a trusted project artifact, not an upload
format for untrusted joblib files.
