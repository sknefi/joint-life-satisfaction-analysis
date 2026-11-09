# Source data and reproducible derived files

The source is the **Joint EVS/WVS 2017-2022 Dataset, ZA7505, version 5.0.0**
(24 June 2024), produced by EVS and WVS and archived by GESIS.

- Dataset DOI: https://doi.org/10.4232/1.14320
- Official download and documentation: https://www.worldvaluessurvey.org/WVSEVSjoint2017.jsp
- Source CSV: `data/raw/evs_wvs_dataset.csv`
- Expected source SHA-256: `bb9094400071c37a0e43fd8b5a21875303d0329f57b51a0ed870fc278659258f`
- Official variable report: download the June 2024 v5 codebook to `docs/ZA7505_cdb.pdf`.

Obtain the files through official access and comply with the producer's usage
terms. This repository does not redistribute the respondent-level survey.
The original CSV is immutable: do not overwrite negative missing codes, filter
it in place or replace it with an edited version.

Run `make data` to select `study == 1`, remove the five `_WVS7` fields, validate
59,438 rows and 226 columns, and generate `processed/evs_v5_0.parquet` plus its
provenance manifest. These files are disposable, reproducible local artifacts.
The builder preserves -1 (don't know), -2 (no answer), -3 (not applicable),
-4 (not asked), -5 (other missing).

Develop uses these codes as missing only in its modelling representation; the
raw data and audit retain their original meanings. Its primary predictor set is
X001, X003, X025R, X028, X047E_EVS5, A009, A165, A173 and cntry_AN; Y is A170.
The local respondent split manifest and out-of-fold probability checkpoints live
in ignored `02_develop/local/`, never in Git or the distributable package.

Aggregate descriptive inference uses all 36 country samples in a separate,
pre-specified pipeline. It does not evaluate prediction models on final test
cases. Predictive training uses 30 countries, with six held out for Assure.

Synthetic example files contain invented profiles only. Neither installed
package tests nor the quickstart needs access to the survey CSV.
