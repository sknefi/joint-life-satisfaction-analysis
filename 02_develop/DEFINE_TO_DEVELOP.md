# Continuity from Define to Develop

This crosswalk compares the submitted Define report sources with the audited
Develop revision v0.1.2. Define is preserved as the original problem definition;
changes are declared in Develop rather than retroactively hidden in Define.

## What stays the same

| Define commitment | Develop implementation / evidence |
|---|---|
| Joint EVS/WVS v5.0.0; EVS `study == 1`; 2017-2021 | Same immutable CSV and derived EVS Parquet; 59,438 respondents / 36 source countries / 226 available columns. |
| One respondent per row; pooled cross-section, not a panel | Same observational unit and limitations. No person-level causal follow-up is invented. |
| A170 ordinal life satisfaction 1-10 | Same target, support and class order; point output is the probability distribution's median. |
| High satisfaction means scores 7-10 | Same primary threshold, fixed before modelling. Scores 8-10 and weighted medians are sensitivity checks, not replacements selected for better-looking results. |
| Core: sex, age, education, employment, EVS income, health, trust and control | Exact same eight core survey fields, plus country. `A008` happiness remains a separate near-proxy sensitivity. |
| EVS income X047E_EVS5, not X047_WVS7 | Same income construct and EVS-only processing. |
| Negative missing codes; age 82 means 82+ | Raw codes preserved; missingness handled only in fitted representations, inside each fold. |
| Median baseline, ordinal regression and a flexible alternative | Empirical median baseline, ordinal all-threshold logistic, random forest and histogram gradient boosting. A numeric linear loss sensitivity is explicitly auxiliary. |
| Primary within-country holdouts; separate whole-country transfer assessment | Within-country training CV, grouped-country training diagnostics and two untouched final prediction tests. |
| MAE, class probabilities, country/subgroup error and calibration | MAE/log loss/RPS, subgroup CV aggregates and country-specific OOF reliability bins. These are training diagnostics, not final Assure conclusions. |
| Compare with/without happiness; report a demographics-only benchmark | Core and happiness fits; a strictly demographic specification X001/X003/X025R plus country is now added. The older demographic/economic variant is correctly retained under its separate name. |
| Counts and full 1-10 distributions by income, employment and country | Training-scope `group_ordinal_distributions.csv`, including country-by-income/employment groups; tiny groups suppressed. |
| Check conclusions using the full scale / median | `threshold_sensitivity.csv` and `define_continuity.json`: primary 7-10, alternative 8-10 and weighted medians; full ten-category distributions retained. |
| gwght within country; country-size or population-size pooling | Same survey-weight roles. Training-partition inverse-retention adjustment is additionally required and explicitly described. |
| Employment intervention cannot be identified from the cross-section | Same causal question and negative feasibility conclusion; N/A effect and N/A causal SE, not an association relabelled as an effect. |

## Declared changes and their implications

1. **Inferential population: 36 to 30 countries.** Define asks about all 36 EVS
   country populations. Develop's training-only fitted inference is restricted to
   the 30 training countries, with six countries reserved for transfer testing.
   This is a genuine scope revision, not an identical fulfilment of the original
   36-country estimand. Reports I/II explicitly name the revision. No 30-country
   result is presented as a result for all 36 countries. The corresponding
   unweighted group descriptions in Develop are also training-scope, not an
   updated group description of all 59,438 original respondents.
2. **Sample sizes have different meanings.** 59,438 is the source EVS sample;
   59,122 have valid A170; 48,365 is Define's complete target/core-predictor count
   over all source countries. The 34,740 training cases result from country and
   respondent holdouts, while retaining incomplete predictors using fold-local
   handling. These numbers do not refer to the same subset.
3. **Context candidates were finalized.** Define lists country, year and interview
   mode as candidates. The primary model keeps country and omits year/mode to
   reduce reliance on fieldwork protocol and keep its prediction inputs focused.
   This is a feature-selection decision, not a claim that year/mode were always
   unavailable or inherently leaked the outcome.
4. **Probability-based estimation is still conditional.** National strata/PSU
   identifiers are unavailable in the common file. The supplied bootstrap does
   not fulfil a stronger claim of complete complex-survey inference; its
   approximation and nonresponse/measurement limits are explicit.
5. **Product scope is narrower than all-source-country prediction and proven imputation.** Define proposes research
   imputation if validated. The released model currently supports 30 training
   country contexts; the six transfer-test countries are explicitly unsupported. Develop supplies a research tool validated on observed
   targets; it does not prove validity for people with missing A170 or offer
   intervention recommendations.

## Promises that belong to later evaluation

- Assure must evaluate the untouched same-country test and six held-out-country
  test. It must report country/subgroup performance and appropriate uncertainty;
  current grouped CV is not a substitute for that final assessment.
- The cross-country relationship-stability question is only partly addressed by
  training diagnostics: similar prediction errors alone do not prove equal
  associations. Assure should compare country-specific socioeconomic gaps as
  well as predictive transfer.
- Design-aware uncertainty needs national design information. A country-level
  resampling analysis of transfer performance remains a later evaluation step.
- Later-wave / temporal external validation requires suitable later or separately
  collected data. One cross-sectional wave cannot establish future-period
  performance; no such result is claimed in Develop.
- Causal estimation still needs new longitudinal or experimental evidence.

## Reproduction

Run `make define-continuity` after the original training run/checkpoints are
available. It fits only the added availability sensitivity and computes
descriptive/country-calibration diagnostics on training cases. It never reselects
the frozen release model or evaluates a final test. Submitted aggregate evidence
is available without raw data; recomputing requires the documented source.
