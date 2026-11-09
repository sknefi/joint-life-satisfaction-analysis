# Develop subject compliance audit

Audit date: 9 November 2026. Audited package/report revision: **v0.1.1**.
The Part II prediction model is the unchanged frozen v0.1.0 artifact; the audit
does not reselect it after production validation. No promise of a grade is made.

Statuses: **Covered** = a concrete deliverable/evidence is present;
**Qualified** = evidence is supplied with a material scientific limitation;
**External** = cannot be verified from the project files/local tests.

## Part I: Candidates and Assumptions

Source: `subject/model_development_report_part1_models.pdf`.

| Requirement | Status | Concrete evidence |
|---|---|---|
| Work from the Define questions; identify revisions | Covered | Report I sections 1-3 and 6: prediction unchanged; population question explicitly narrowed from 36 to the 30 training countries. |
| At least three prediction approaches plus a baseline | Covered | Ordinal all-threshold logistic, random forest and histogram gradient boosting; empirical median/frequency baseline. Bagging and sequential boosting are different approaches, despite both using trees. |
| Match outcome support and intended prediction moment | Covered | A170 is ordinal 1-10; ten probabilities and distribution median; predictors available after the non-target questionnaire. Numeric distances assumed only in the labelled auxiliary loss sensitivity. |
| Choose appropriate inference and causal approaches | Qualified | Weighted ratio estimates with declared target/weights; prospective target-trial/doubly robust causal proposal. EVS does not identify the employment intervention. |
| Overview table, one row per question | Covered | First table of Report I. |
| Explain assumptions, plausibility, bias/variance/invalid uncertainty and repairs | Covered | Candidate table; inferential selection versus dependence discussion; separate causal identification and estimation assumptions. |
| Finish each approach with an explicit verdict | Covered | Exact verdict language added to the four prediction approaches, inference and causality. |
| Expected ranking and what would change it | Covered | Report I section 5: boosting expected to win; noisy signal may favour ordinal; calibration/group transfer could reverse the choice. |
| Causal confounders, timing, overlap, consistency, spillovers and direction | Covered | Report I section 7: prior health can create upward confounding; current income can mediate; identification remains absent. |
| Dataset/source and concise labelled prediction, inference, causality sections | Covered | DOI/source references, three-page PDF. |

## Part II: Training and Tuning

Source: `subject/model_development_report_part2_train.pdf`.

| Requirement | Status | Concrete evidence |
|---|---|---|
| Fit approaches on training data only | Covered | 34,740 training cases; all tuning, added loss/seed experiments and revised inferential ratios use this partition. Six held-out countries and same-country final tests are not evaluated. Production validation is separate, after the choice is frozen. |
| State loss/likelihood and justify its target | Covered | Report II sections 1-3; all-threshold logistic is explicitly a surrogate, not categorical ordered-logit MLE; forest criterion is local split impurity. |
| Fit an alternative criterion and explain changed estimates/predictions | Covered | `results/loss_sensitivity.json`: identical unpenalized linear function class, squared versus Huber loss (delta=1); five training-only folds; actual point-prediction changes, MAE/MSE, fitted coefficients and optimizer diagnostics. Original Gini/entropy comparison is additional evidence, not the sole global-loss comparison. |
| Tune all prediction candidates within training; fold-local preprocessing | Covered | `training.py`, `models.py`, `trials.json`; tests verify split isolation and that validation cannot change fitted encoding statistics. |
| Report search method, space and chosen values; extend boundary ranges | Covered | Ordinal/forest grids, eight seeded boosting samples, one declared boundary extension; all tried configurations retained. This is a bounded search, not a proof of an unconstrained optimal hyperparameter. |
| Training table: criteria, learned parameters, hyperparameters, optimizer | Covered | Report II first table includes prediction, inference and the non-estimable causal row; full numerical coefficients/settings in parameter JSON. |
| Software/version/function, starts, tolerance, iterations, seed and convergence | Covered | Report II section 5 and JSON: analytic ordinal gradient/projected-gradient check, empirical starting cutpoints, Huber OLS start and gradient, tree settings/early stopping. Closed-form operations explicitly have no iterative optimizer. |
| Multiple starts/seeds for relevant non-convex procedures | Covered | `seed_stability_extended.json`, seeds 42/2026/2027, fixed configurations, CV spread and best/range of training log loss. Convex OLS/Huber/ordinal fits do not require random local starts; greedy trees do not provide a global-optimum certificate. |
| At least one CV curve | Covered | `figures/cv_curve.png`, Report II page 2. |
| Inference estimates, standard errors and how computed | Qualified | Training-only weighted ratios and differences; 1,000 fixed-country respondent bootstraps, split-retention correction. Intervals are approximate because definitive national PSU/stratum identifiers are unavailable. They are not presented as full complex-survey intervals. |
| Causal estimate and standard error | Qualified | Explicit N/A in Reports I/II: cross-sectional EVS lacks baseline intervention and follow-up outcomes. A descriptive employment gap is reported with its own uncertainty, never substituted for a causal effect. This is the non-identification case expressly allowed in Part I. |
| Explain revisions since Part I | Covered | Reports identify the post-Part-I audit loss supplement and the 30-country inferential restriction; the three main candidates and winner remain unchanged. |
| Reproducible numbers/code; no final-test comparison | Covered | Configurations, source hashes, exact runtime, aggregate outputs, raw-source instructions and Makefile targets. `prediction_test_evaluations` remains zero. |

## Part III: Production / GitHub repository

Source: `subject/model_development_report_part3_production.pdf`.

| Requirement | Status | Concrete evidence |
|---|---|---|
| One reusable thing based on Parts I/II; purpose/audience/use | Covered | Installed `evs-predict` command, frozen model and preprocessing; research-use scope and examples in README / one-page Report III. |
| README, functions, pyproject.toml | Covered | Installable wheel/source package, modular `src/evs_model`, documented entry points. |
| Tests run through GitHub Actions after changes | External | Workflow installs pinned runtime, runs all tests, example and saved-reference product verification. These checks pass locally; remote CI conclusion was not authenticated and is not claimed. |
| Gitignore for data/secrets; data download documentation | Covered | `data/README.md`, immutable source rules; no source CSV, private split IDs or environments in the submission kit. |
| Versioned pip-installable release and notebook | Covered | Existing v0.1.0 model; v0.1.1 audited package, tagged source and submission ZIP with wheel. Executed `notebooks/quickstart.ipynb`. The kit can be installed without a GitHub login; a separate GitHub Releases UI object is not claimed. |
| Same answers as the saved Part II model | Covered | 120 invented reference profiles and saved outputs; 1e-12 tolerance and class/probability checks. Verification no longer needs ignored training checkpoints. |
| Only prediction-time information; no target leakage | Covered | Strict schema rejects A170, IDs, weights and extra inputs; fold-local preprocessing and split tests. |
| Bad inputs, out-of-range and unseen categories | Covered | Missing codes handled; unsupported countries, malformed/fractional/out-of-support values rejected; atomic output and input-overwrite protection. Dates are not model inputs. |
| Reproducible installation and execution elsewhere | Covered | Clean installed-wheel environment and independently extracted submission-kit check; seeds, versions, metadata, reference examples and checksums. |
| Honest uncertainty / coverage if intervals are displayed | Covered | No individual interval is displayed, so an 80% interval-coverage claim is not applicable. Category probabilities, reliability bins and limitations are supplied. Inferential approximate intervals are separately labelled. |
| AI-written code verified by tests | Covered | 21 automated tests, numerical gradient checks, saved reference parity and installed-command tests. Test success does not prove all statistical assumptions. |
| Approximately one-page report, runnable artifact/link | Covered | Report III is one page, with concrete commands; standalone submission ZIP plus repository link. |
| No restricted data, personal records or credentials/history | Covered with limits | Allowlisted ZIP excludes Git history and raw/local data. Original 20 tracked revisions had no raw CSV/private-key/.env paths and no high-confidence credential-pattern matches. This is an automated audit, not proof against every conceivable secret format. |

## Changes and remaining limits

1. Added exact verdicts, clearer confounding direction and identification versus
   estimation assumptions; no causal number is invented.
2. Strengthened the alternative-criterion requirement with actual squared/Huber
   fitting and three-seed checks; no production-driven reselection.
3. Restricted fitted inferential results to training cases/30 countries. Known
   split-selection probabilities correct the country-by-outcome partition.
4. Added portable saved-reference production tests and a data-free, installable
   submission kit. The original prediction-model checksum remains unchanged.
5. **External checks remain:** remote GitHub Actions conclusion, the teacher's
   access to the private repository, and Moodle deadline/upload rules. Supply the
   ZIP with the PDFs to remove the repository-access dependency.
6. **Scientific limits remain:** unidentifiable employment intervention, potentially
   MNAR/nonresponse bias, imperfect calibration and unavailable full survey design.
   These are disclosed limits of the evidence, not claims that the data were fixed.
