# Model Development Report - Part 1: Candidates and Assumptions | Life satisfaction across EVS countries



## 1. Questions, candidates and commitments

<b>Data and scope.</b> Joint EVS/WVS 2017-2022 v5.0.0, EVS records only (study = 1): 59,438 respondents in 36 countries, fieldwork 2017-2021. One row is one person; this is a clustered pooled cross-section, not a longitudinal panel. The response is A170, ordinal life satisfaction 1-10.

| Question / goal | Approach and rationale | Critical assumption |

|---|---|---|

| Prediction: an unseen EVS-style respondent in a represented country | Empirical median/frequency baseline; regularized ordinal logistic; random forest; histogram gradient boosting | Inputs known after the non-target questionnaire; relationships and measurement transfer to unseen respondents. |

| Inference: population proportions with A170 >= 7, and income/employment gaps | Country-specific weighted ratios; equal-country pooling; population-size-weighted sensitivity; approximate bootstrap uncertainty | Survey weights adequately adjust observed margins; residual selection and within-country dependence remain limitations. |

| Causality: effect of obtaining paid work among initially unemployed adults | Not identified by EVS; propose a prospective panel / target trial with pre-employment adjustment | Temporal ordering, pre-treatment common causes, overlap, consistency and no material spillovers. |


## 2. Prediction case and information available

Predict after an EVS-style respondent has answered the non-target questions, before A170 is observed. Intended use is a research demonstration and possible future imputation research, conditional on validation. It is not an intervention recommendation or a claim about present-day populations.

<b>Core inputs:</b> X001 sex; X003 age; X025R education; X028 employment; X047E_EVS5 household-income decile; A009 health; A165 trust; A173 control; cntry_AN country. Exclude IDs, weights, fieldwork dates, year and interview mode from the primary model. A008 happiness is a separate near-proxy sensitivity analysis; a demographic/economic-only specification tests dependence on subjective items.

<b>Representation:</b> age and age squared, median-imputed within each training fold, standardized using that fold; a missing-age indicator. Other survey codes are explicitly one-hot encoded, including a missing category. Category codes are not assumed to be equally spaced. Age 82 denotes 82+. The raw CSV and its negative missing codes remain immutable.


## 3. Frozen evaluation protocol

Seed 42 selects six countries using country labels only for a final transfer test. In the remaining 30, valid-target respondents are partitioned within country x outcome strata: approximately 70% training, 10% production validation, 20% final same-country test. Rounding is documented. Missing targets are excluded from prediction fitting; missing predictors do not cause complete-case deletion.

Five-fold within-country CV tunes candidates on training data only. Five-fold country-group CV of the frozen candidate configurations checks transfer within the training countries. Preprocessing is refitted inside every fold. Production validation is opened only after the winner is frozen. Both final prediction tests are reserved for Assure.


## 4. Candidate assumptions, objectives and possible failures

| Candidate | Assumptions and consequences | Repair / verdict |

|---|---|---|

| Baseline | Training outcome frequencies transfer. A global median ignores country and individual variation: potentially high bias, low variance. | Mandatory benchmark; assumptions plausible only as a reference. |

| Ordinal logistic (all-threshold, L2) | One additive latent score with ordered logistic thresholds; shared slopes across thresholds. Missed nonlinearities/interactions or threshold-specific effects create bias. L2 reduces variance; probabilities need calibration checks. | Quadratic age and explicit categories; tune L2. Violations may be harmful; compare with flexible candidates. |

| Random forest classifier | Enough observations support local partitions and interactions. Sparse subgroups and deep trees increase variance; leaf averaging can flatten extremes. Classifier does not exploit outcome order during fitting. | Limit depth, impose substantial leaf sizes, average 200 trees; judge on ordinal-aware metrics. Assumptions plausible with regularization. |

| Histogram gradient boosting classifier | Useful signal can be approximated by shallow interactions. Sequential fitting can overfit noise; nominal multiclass loss does not encode score distance. No reliable extrapolation to new contexts. | Small learning rates and trees, regularization and fold-local early stopping. Plausible, with careful tuning and group validation. |

<b>Objectives:</b> baseline median minimizes empirical absolute error; its probabilities are empirical frequencies. The ordinal estimator minimizes the sum of nine binary threshold logistic losses plus alpha/2 times squared coefficient norm (an all-threshold surrogate, not exact categorical ordered-logit likelihood). Forests greedily reduce Gini impurity. Boosting minimizes multiclass log loss through successive trees.

<b>Alternative criterion:</b> refit the selected forest configuration with Shannon entropy instead of Gini. Keep its other hyperparameters fixed to isolate the criterion change. This compares local split objectives, not two globally optimized forest likelihoods. Evaluate probability and point-prediction differences out of fold.


## 5. Tuning, success and expected ranking

Initial search: ordinal alpha {0.1, 1, 10, 100}; forest 200 trees, depth {6,10}, minimum leaf {20,50}, max_features {sqrt,0.7}; boosting eight seeded combinations of learning_rate {0.05,0.1}, leaves {7,15}, minimum leaf {50,100}, L2 {0,1}; up to 200 iterations. A pre-specified one-step outward extension follows boundary optima. Tree extension changes depth/leaf-size together as a bounded sensitivity, not an exhaustive expanded grid.

<b>Selection:</b> minimize mean CV MAE of the predicted distribution's median; break exact metric ties using RPS. Prefer ordinal if within one standard error of the best candidate. Retain baseline if no model improves it. Report log loss, normalized ranked probability score (RPS), Brier score for A170 >= 7, calibration and subgroup error. Probabilities are estimated distributions, not a confidence interval for an individual's outcome.

<b>Expectation:</b> boosting may win through nonlinear health/control/income interactions; ordinal may be competitive because self-report noise limits useful complexity; forest may be more conservative. Similar CV errors, poor calibration, or worse country transfer would change this ranking. No performance claim is made before fitting.


## 6. Inference: estimand, weighting and uncertainty

Estimate country-specific proportions of A170 scores 7-10 and marginal income/employment differences among adults in private households represented by the 36 EVS country surveys during 2017-2021. Within-country estimates use gwght. Primary pooled ratios use gwght x wght_eq1000 (equal-country-size scaling); sensitivity ratios use gwght x pwght (population-size scaling). Unweighted results describe the observed sample. Finite differences in national gwght totals mean the first pooled ratio is not an exactly equally normalized average of 36 country means.

Pre-specify income contrast deciles 9-10 minus 1-2; employment contrast paid full/part-time work (X028=1/2) minus unemployment (X028=7). These are descriptive associations, not adjusted causal effects. Report counts, Kish effective sample size and approximate 95% intervals. Suppress estimates with raw or effective n below 30.

Use 1,000 respondent bootstrap draws separately within each fixed country, recalculating weighted ratios and contrasts. The common file has no definitive PSU/stratum identifiers. These intervals therefore approximate conditional sampling variability under iid respondents within country; they can be too narrow under unobserved cluster dependence and are not full survey-design intervals. Do not cluster a national estimate on its sole country.

Income missingness is 14.70% and potentially MNAR. Compare observed-income and missing-income respondents, report country/group coverage, and avoid claiming that complete-case ratios or survey weights remove this bias. More respondents reduce variance but do not eliminate nonresponse, measurement or selection bias. Self-report, translations and modes can change the measured construct across countries.


## 7. Causality: identification before estimation

The question remains: among adults 18-64 unemployed at baseline, what is the average effect on A170 at 12 months of entering paid employment within three months versus remaining unemployed? EVS observes current employment and current satisfaction once; neither transition timing nor baseline satisfaction is available.

Prior well-being, health, job history, household circumstances and labour-market opportunities influence both employment and satisfaction. Reverse causation is plausible. Current income may mediate employment's effect and should not automatically be controlled when targeting a total effect. Cross-sectional regression or feature importance does not identify this intervention.

<b>Proposed repair:</b> follow baseline-unemployed adults prospectively, measure pre-treatment common causes and well-being, record job entry and quality, and pre-specify a target trial. With defensible conditional exchangeability, overlap and consistency, use doubly robust outcome/propensity adjustment with cross-fitting and appropriate dependence-aware uncertainty. Check overlap, balance, attrition and spillovers. A randomized job-placement offer identifies the offer effect, not automatically employment's effect.

<b>Verdict:</b> the causal effect is not identified from the supplied EVS cross-section. Part II will report descriptive employment associations with qualified uncertainty, but no fabricated treatment effect or causal standard error.


## 8. Reproduction and references

The implementation will preserve source hashes, split manifests locally, seeds, versions, configurations, optimizer diagnostics and all report-generating aggregates. Final prediction-test scores will not appear in Develop. Part III will be an installable GitHub repository, with no web hosting or deployment.

EVS/WVS (2024), Joint EVS/WVS 2017-2022, ZA7505 v5.0.0, <link href="https://doi.org/10.4232/1.14320" color="#168C8C">doi:10.4232/1.14320</link>. Variable Report, June 2024: supports, missing codes, weighting and anonymisation. Rennie &amp; Srebro (2005), Loss Functions for Preference Levels. scikit-learn documentation: RandomForestClassifier and HistGradientBoostingClassifier. Source: <link href="https://github.com/sknefi/joint-life-satisfaction-analysis" color="#168C8C">github.com/sknefi/joint-life-satisfaction-analysis</link>.
