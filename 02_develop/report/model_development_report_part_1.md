# Model Development Report - Part 1: Candidates and Assumptions | Life satisfaction across EVS countries



## 1. Questions, candidates and commitments

<b>Data and scope.</b> Joint EVS/WVS 2017-2022 v5.0.0, EVS records only (study = 1): 59,438 respondents in 36 countries, fieldwork 2017-2021. One row is one person; this is a clustered pooled cross-section, not a longitudinal panel. The response is A170, ordinal life satisfaction 1-10.

| Question / goal | Approach and rationale | Critical assumption |

|---|---|---|

| Prediction: an unseen EVS-style respondent in a represented country | Empirical median/frequency baseline; regularized ordinal logistic; random forest; histogram gradient boosting | Inputs known after the non-target questionnaire; relationships and measurement transfer to unseen respondents. |

| Inference: population proportions with A170 >= 7, and income/employment gaps | Training-only country-weighted ratios; equal-country and population-size pooling; approximate bootstrap uncertainty | Survey weights adequately adjust observed margins; residual selection and within-country dependence remain limitations. |

| Causality: effect of obtaining paid work among initially unemployed adults | Not identified by EVS; propose a prospective panel / target trial with pre-employment adjustment | Temporal ordering, pre-treatment common causes, overlap, consistency and no material spillovers. |


## 2. Prediction case and information available

Predict after an EVS-style respondent has answered the non-target questions, before A170 is observed. Intended use is a research demonstration and possible future imputation research, conditional on validation. It is not an intervention recommendation or a claim about present-day populations.

<b>Core inputs:</b> X001 sex; X003 age; X025R education; X028 employment; X047E_EVS5 household-income decile; A009 health; A165 trust; A173 control; cntry_AN country. Exclude IDs, weights, fieldwork dates, year and interview mode from the primary model. A008 happiness is a separate near-proxy sensitivity analysis; separate demographic/economic and strictly demographic benchmarks test input availability. Define listed year/mode as context candidates; the primary model retains country and omits fieldwork metadata to reduce reliance on collection protocol.

<b>Representation:</b> age and age squared, median-imputed within each training fold, standardized using that fold; a missing-age indicator. Other survey codes are explicitly one-hot encoded, including a missing category. Category codes are not assumed to be equally spaced. Age 82 denotes 82+. The raw CSV and its negative missing codes remain immutable.


## 3. Frozen evaluation protocol

Seed 42 selects six countries using country labels only for a final transfer test. In the remaining 30, valid-target respondents are partitioned within country x outcome strata: approximately 70% training, 10% production validation, 20% final same-country test. Rounding is documented. Missing targets are excluded from prediction fitting; missing predictors do not cause complete-case deletion.

Five-fold within-country CV tunes candidates on training data only. Five-fold country-group CV of the frozen candidate configurations checks transfer within the training countries. Preprocessing is refitted inside every fold. Production validation is opened only after the winner is frozen. Both final prediction tests are reserved for Assure.


## 4. Candidate assumptions, objectives and possible failures

| Candidate | Assumptions and consequences | Repair / verdict |

|---|---|---|

| Baseline | Training outcome frequencies transfer. A global median ignores country and individual variation: potentially high bias, low variance. | Mandatory benchmark. Verdict: Assumptions plausible as a reference. |

| Ordinal logistic (all-threshold, L2) | One additive latent score with ordered logistic thresholds; shared slopes across thresholds. Missed nonlinearities/interactions or threshold-specific effects create bias. L2 reduces variance; probabilities need calibration checks. | Quadratic age, explicit categories, L2 tuning and flexible comparisons. Verdict: Assumptions plausible for same-wave prediction; shared slopes remain a testable risk. |

| Random forest classifier | Enough observations support local partitions and interactions. Sparse subgroups and deep trees increase variance; leaf averaging can flatten extremes. Classifier does not exploit outcome order during fitting. | Limit depth and leaf size; average 200 trees; evaluate ordinal errors. Verdict: Assumptions plausible with regularization. |

| Histogram gradient boosting classifier | Useful signal can be approximated by shallow interactions. Sequential fitting can overfit noise; nominal multiclass loss does not encode score distance. No reliable extrapolation to new contexts. | Small trees/rates, L2 and fold-local stopping. Verdict: Assumptions plausible for represented-country cases; transfer remains uncertain. |

<b>Objectives:</b> baseline median minimizes empirical absolute error; its probabilities are empirical frequencies. The ordinal estimator minimizes the sum of nine binary threshold logistic losses plus alpha/2 times squared coefficient norm (an all-threshold surrogate, not exact categorical ordered-logit likelihood). Forests greedily reduce Gini impurity. Boosting minimizes multiclass log loss through successive trees.

<b>Alternative criterion:</b> refit the selected forest configuration with Shannon entropy instead of Gini. Keep its other hyperparameters fixed to isolate the criterion change. This compares local split objectives, not two globally optimized forest likelihoods. Evaluate probability and point-prediction differences out of fold.

<b>Revision note:</b> the audit additionally compares squared and Huber (delta=1) objectives on the identical numeric linear specification. This is a training-only criterion sensitivity added after the original Part I, not another tuned candidate or a reason to reopen production validation.


## 5. Tuning, success and expected ranking

Initial search: ordinal alpha {0.1, 1, 10, 100}; forest 200 trees, depth {6,10}, minimum leaf {20,50}, max_features {sqrt,0.7}; boosting eight seeded combinations of learning_rate {0.05,0.1}, leaves {7,15}, minimum leaf {50,100}, L2 {0,1}; up to 200 iterations. A pre-specified one-step outward extension follows boundary optima. Tree extension changes depth/leaf-size together as a bounded sensitivity, not an exhaustive expanded grid.

<b>Selection:</b> minimize mean CV MAE of the predicted distribution's median; break exact metric ties using RPS. Prefer ordinal if within one standard error of the best candidate. Retain baseline if no model improves it. Report log loss, normalized ranked probability score (RPS), Brier score for A170 >= 7, calibration and subgroup error. Probabilities are estimated distributions, not a confidence interval for an individual's outcome.

<b>Expectation:</b> boosting may win through nonlinear health/control/income interactions; ordinal may be competitive because self-report noise limits useful complexity; forest may be more conservative. Similar CV errors, poor calibration, or worse country transfer would change this ranking. No performance claim is made before fitting.


## 6. Inference: estimand, weighting and uncertainty

<b>Revised inferential question:</b> among private-household adults represented by the 30 training-country EVS surveys in 2017-2021, what are weighted high-satisfaction proportions and income/employment gaps? Define covered 36 countries; Develop narrows the inferential scope to honour training-data-only fitting. No estimate for all 36 countries is claimed here. National probability sampling and supplied calibration weights support cautious population inference, conditional on residual nonresponse assumptions. Within-country analysis weights are gwght / pi, where pi is the known training retention fraction within country x A170 strata (rounding makes it differ from 0.7). Pooled weights additionally multiply by wght_eq1000 or, in sensitivity, pwght. These size-scaled ratios are not exactly normalized averages of country means.

Pre-specify income contrast deciles 9-10 minus 1-2; employment contrast paid full/part-time work (X028=1/2) minus unemployment (X028=7). These are descriptive associations, not adjusted causal effects. Report counts, Kish effective sample size and approximate 95% intervals. Suppress estimates with raw or effective n below 30.

Use 1,000 respondent bootstrap draws separately within each fixed country, recalculating weighted ratios and contrasts. The common file has no definitive PSU/stratum identifiers. These intervals therefore approximate conditional sampling variability under iid respondents within country; they can be too narrow under unobserved cluster dependence and are not full survey-design intervals. Do not cluster a national estimate on its sole country.

Income missingness is potentially MNAR: compare observed/missing-income groups, but do not claim to repair its bias. Population interpretation also assumes remaining target nonresponse is ignorable after weighting. Nonresponse and measurement errors bias estimates; ignored clusters principally invalidate uncertainty. <b>Verdict for a full design-based claim: Violated and likely harmful: repair or replace.</b> Obtain national PSU/stratum information; retain only explicitly approximate intervals meanwhile.


## 7. Causality: identification before estimation

The question remains: among adults 18-64 unemployed at baseline, what is the average effect on A170 at 12 months of entering paid employment within three months versus remaining unemployed? EVS observes current employment and current satisfaction once; neither transition timing nor baseline satisfaction is available.

Prior well-being, health, job history and labour-market opportunities influence both employment and satisfaction. Better prior health plausibly increases both, creating upward confounding of a positive employment association; the net direction is not identified. Current income may be a mediator; conditioning on it can remove part of the total effect. No cross-sectional feature importance identifies the intervention.

<b>Proposed repair:</b> follow baseline-unemployed adults prospectively, measure pre-treatment common causes and well-being, record job entry and quality, and pre-specify a target trial. Separate <b>identification</b> (pre-treatment exchangeability, overlap, consistency/no spillovers) from <b>estimation</b> (a correct outcome or propensity nuisance model for doubly robust consistency; adequate cross-fitting/rates for influence-function uncertainty). Check balance, overlap and attrition; use design-aware standard errors. An employment-programme offer identifies the offer effect, not automatically employment's effect.

<b>Verdict: Violated and likely harmful: repair or replace.</b> EVS cannot identify the employment intervention. The causal estimate and its standard error are therefore N/A, rather than zero or an employment-association coefficient.


## 8. Reproduction and references

The implementation will preserve source hashes, split manifests locally, seeds, versions, configurations, optimizer diagnostics and all report-generating aggregates. Final prediction-test scores will not appear in Develop. Part III will be an installable GitHub repository, with no web hosting or deployment.

EVS/WVS (2024), Joint EVS/WVS 2017-2022, ZA7505 v5.0.0, <link href="https://doi.org/10.4232/1.14320" color="#168C8C">doi:10.4232/1.14320</link>. Variable Report, June 2024: supports, missing codes, weighting and anonymisation. Rennie &amp; Srebro (2005), Loss Functions for Preference Levels. scikit-learn documentation: RandomForestClassifier and HistGradientBoostingClassifier. Source: <link href="https://github.com/sknefi/joint-life-satisfaction-analysis" color="#168C8C">github.com/sknefi/joint-life-satisfaction-analysis</link>.
