# Model Development Report - Part 2: Training and Tuning | Objectives, validation and uncertainty



## 1. Training results: validation inside training only

EVS subset: 59,438 respondents / 36 countries; A170 has 59,122 valid responses. The fixed split yields 34,740 training, 5,007 production-validation, 10,079 same-country final-test and 9,296 held-out-country final-test cases. The 316 missing targets are excluded from predictive learning. Counts differ slightly from nominal percentages due to per-stratum rounding.

Held-out countries: AT, FR, GB, LT, MK, RS. Neither final prediction test was used for tuning or model comparison. Five within-country folds share country contexts but not respondents; five group folds remove entire training-country contexts.

| Approach | Criterion | Fitted summary | Chosen tuning | Optimizer | CV MAE +/- SE<br/>Log loss<br/>RPS |

|---|---|---|---|---|---|

| baseline | Empirical absolute loss / frequencies | Empirical frequencies | None | Closed form | 1.565 +/- 0.009<br/>1.999<br/>0.1251 |

| ordinal | Threshold logistic + L2 | 81 coefficients + 9 cutpoints | alpha=0.01 | L-BFGS-B; analytic gradient | 1.255 +/- 0.007<br/>1.802<br/>0.1001 |

| forest | Gini split gain | 200 trees | depth 14; leaf 10; mtry 0.7 | Greedy CART; seed 42 | 1.250 +/- 0.005<br/>1.753<br/>0.0987 |

| boosting | Multiclass log loss | 780 trees | lr 0.1; leaves 15; leaf 50; L2 1.0 | Histogram boosting; early stop | 1.225 +/- 0.006<br/>1.715<br/>0.0963 |

<b>Frozen selection:</b> boosting; rule: lowest mean CV MAE. MAE uses the median of the predicted 10-category distribution. SE is the sample SD of five fold MAEs divided by sqrt(5): a descriptive tuning uncertainty, not a survey-design or independent-fold confidence interval.


## 2. Criteria and representation

Ordinal fitting minimizes all-threshold logistic surrogate loss plus L2; the baseline uses observed frequencies. Forests greedily improve Gini impurity; histogram boosting minimizes multinomial log loss. Final selection instead targets CV MAE; log loss and RPS check probability quality. No class balancing is applied, because it would change the learned prevalence. All predictive fitting is unweighted; survey-weighted inference answers a separate population question.

Age and age squared use fold-specific median imputation and scaling; a missing-age indicator is added. Nominal and ordinal survey items use explicit categories, including missingness. Country holdouts receive unknown-country indicator blocks during group CV; the public command rejects unsupported countries. The production artifact contains only 30 training-country contexts.


## 3. Alternative split criterion

| Fixed forest settings; changed criterion | CV MAE | Log loss | RPS |

|---|---|---|---|

| Gini | 1.2504 | 1.7530 | 0.09870 |

| Shannon entropy | 1.2535 | 1.7685 | 0.09876 |

Changing only the criterion changes CV MAE by +0.0031. This is a controlled comparison of greedy split objectives; it is not evidence that the forest finds a global likelihood optimum. Probability and point-score changes are both reported.


## 4. Search, chosen hyperparameters and sensitivity

| Candidate | Selected hyperparameters |

|---|---|

| baseline | {} |

| ordinal | {&quot;alpha&quot;: 0.01} |

| forest | {&quot;max_depth&quot;: 14, &quot;max_features&quot;: 0.7, &quot;min_samples_leaf&quot;: 10} |

| boosting | {&quot;l2_regularization&quot;: 1.0, &quot;learning_rate&quot;: 0.1, &quot;max_leaf_nodes&quot;: 15, &quot;min_samples_leaf&quot;: 50} |

Initial search and one-step boundary extensions follow Part I. Every candidate uses five folds and identical split indices; no preprocessing is shared across folds. Forest size is fixed at 200 trees. Boosting uses at most 200 iterations, a 15% internal training-fold validation fraction, patience 15, and seed 42. Complete trial spaces, fold results and timings are in results/trials.json.

| Frozen selected-family specification | CV MAE | Log loss | RPS |

|---|---|---|---|

| demographic_economic | 1.447 | 1.892 | 0.1140 |

| with_happiness | 1.102 | 1.625 | 0.0870 |

Sensitivity fits reuse the selected family's hyperparameters without retuning; differences assess predictor availability, not separately optimized competitors. Adding happiness tests near-proxy dependence; removing subjective inputs tests whether survey-like subjective answers are essential.

![Training-only CV curve](cv_curve.png)


## 5. Optimization and fitted parameters

<b>Ordinal:</b> L-BFGS-B with analytic gradients, ordered-threshold increment constraints, maximum 2,000 initial iterations, initial ftol=1e-9; retry at stricter tolerance when necessary. Final fit: 135 iterations; success=True; objective 100772.10; projected gradient per training row 2.8e-05. <b>Boosting:</b> final fit 78 iterations / 780 trees; internal validation log loss 1.9991 to 1.7282. Alternate-seed details are recorded in seed_stability.json.

Forests use greedy CART and bootstrap aggregation; there is no continuous gradient convergence test. Boosting uses greedy histogram trees with early stopping, which is part of regularization rather than a certificate of global optimality. A second seed is reported for the chosen tree configurations as an optimizer/randomization stability check. Full settings, thresholds, coefficients, tree counts and diagnostics are saved as JSON; fitted estimators are serialized separately.


## 6. Transfer diagnostics and uncertainty

| Frozen candidate | Grouped CV MAE | Log loss | RPS |

|---|---|---|---|

| baseline | 1.565 | 2.003 | 0.1254 |

| ordinal | 1.282 | 1.822 | 0.1022 |

| forest | 1.281 | 1.782 | 0.1008 |

| boosting | 1.266 | 1.760 | 0.0997 |

Group CV is a secondary training-country diagnostic, not nested CV or a score on the six held-out test countries: configurations were chosen using within-country CV across the training sample. It exposes transfer to unfamiliar country indicator blocks. Country/subgroup errors and reliability bins are provided as aggregates. Predicted category probabilities express model uncertainty; no individual prediction intervals are claimed.


## 7. Population estimates and descriptive gaps

| Overall weighting | High-satisfaction proportion | Approx. SE | Approx. 95% interval |

|---|---|---|---|

| unweighted | 72.51% | 0.18 pp | 72.17-72.86% |

| equal_country | 70.99% | 0.24 pp | 70.55-71.49% |

| population | 68.60% | 0.47 pp | 67.73-69.58% |

| Descriptive contrast | Difference | Approx. SE | Approx. 95% interval |

|---|---|---|---|

| income high minus low | +31.74 pp | 0.82 pp | +30.06 to +33.31 pp |

| paid minus unemployed | +18.99 pp | 0.97 pp | +17.02 to +20.94 pp |

These pre-specified inferential descriptions use all 36 country samples separately from predictive model selection. Within-country gwght adjusts observed margins; pooled equal-country-size and population-size weighting target different summaries. Intervals use 1,000 iid respondent bootstraps within fixed countries. They omit unobserved PSU dependence, do not estimate uncertainty over a hypothetical population of countries, and do not remove selection or measurement bias. Small or low-effective-size groups are suppressed.

Income is missing in 14.70% of EVS rows. Equal-country-size-weighted high-satisfaction proportions are 70.84% with observed income and 71.77% with missing income. This diagnoses a potentially selected complete-case population; it does not identify an MNAR correction.


## 8. Causality, reproducibility and remaining evaluation

The paid-employment gap above is an association. The effect of obtaining employment remains unidentified: no pre-employment well-being, transition assignment or 12-month outcome is observed. No causal coefficient or causal standard error is reported. The prospective design and assumptions in Part I remain required.

Environment: Python 3.12.14; scikit-learn 1.9.1; NumPy 2.5.4; SciPy 1.18.1. Seed 42. Input Parquet SHA-256: 978592d03407591d74b1... Full source/code hashes, package versions, split policy and optimizer settings are recorded. Source: EVS/WVS ZA7505 v5.0.0, doi:10.4232/1.14320. Reproduce with make train, make inference and make develop-reports.
