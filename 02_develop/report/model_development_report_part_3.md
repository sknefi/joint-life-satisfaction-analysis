# Model Development Report - Part 3: Production | An installable GitHub research tool



## 1. Product and intended user

An installable, versioned Python repository for students/researchers reproducing EVS life-satisfaction analysis or predicting an omitted A170 response for an EVS-style respondent. Package release 0.1.2 includes the unchanged v0.1.0 Part II boosting model and its complete preprocessing. There is no hosted service or deployment. Repository: <link href='https://github.com/sknefi/joint-life-satisfaction-analysis' color='#168C8C'>github.com/sknefi/joint-life-satisfaction-analysis</link>.


## 2. Install and run

Clone the repository (access required), or unzip the submission kit and open its project folder. The ZIP needs no GitHub login; skip the first two commands when using it. Run the following on macOS/Linux with Python 3.12:

```text
git clone https://github.com/sknefi/joint-life-satisfaction-analysis.git
cd joint-life-satisfaction-analysis
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-model-lock.txt
python -m pip install --no-deps .
evs-predict --input examples/respondents.csv --output predictions.csv
```

Expected message: <b>Predicted 3 respondents; saved predictions.csv.</b> Open that CSV for scores and probabilities. The repository/ZIP includes the model in models/; the wheel installs code only. Prediction needs no survey data. The original dataset and Parquet are not distributed; full analysis requires obtaining the source CSV and creating the Parquet with make data.

<b>Full instructions and project information:</b> see <link href='https://github.com/sknefi/joint-life-satisfaction-analysis#readme' color='#168C8C'>README.md</link> in the project root for installation, inputs, examples, tests, data access and analysis reproduction. The notebook notebooks/quickstart.ipynb provides a walkthrough. Outside the project root, pass --model /path/to/evs_v0_1_0.joblib.


## 3. Inputs, outputs and scope

Input CSV columns: X001, X003, X025R, X028, X047E_EVS5, A009, A165, A173, cntry_AN. Use official survey category codes; blank values and -1..-5 become missing. Age must be 18-82, with 82 interpreted as 82+. Country is mandatory and must be one of the 30 training countries. Output: predicted_score (distribution median), probability_high_7_10 and p_1 through p_10. The predictor rejects A170, identifiers, weights, unexpected columns and invalid categories; writes are atomic.


## 4. Verification as a reusable product

| Check | Observed result |

|---|---|

| Package and regression tests | 21 tests passed; existing profiler checks retained. Clean installed-wheel check: True; executed notebook: True. |

| Artifact parity | 120 synthetic cases; maximum probability difference after save/load and CLI round-trip: 0. Saved Part II reference predictions, class order and probability sums checked; no private training checkpoint is required. |

| Bad inputs and leakage | Tests cover missing codes, malformed/range/category errors, unknown countries, target exclusion, fold-local preprocessing and country isolation. |

| Independent production validation | Frozen model: n=5,007, MAE=1.213, log loss=1.711, RPS=0.0963. Not used to tune or select the model. |

| Automation and reproducibility | GitHub Actions installs the package and runs synthetic-data tests; recorded versions, seeds, hashes and saved preprocessing. Remote CI status is unverified (authenticated access was not available); workflow presence is not a claim of a passed server run. |


## 5. Honest interpretation and maintenance

The probabilities are model estimates for historical EVS-style contexts, not validated individual confidence intervals or causal effects. No interval coverage is claimed. Production reliability bins are saved; final same-country and six-country prediction tests remain for Assure. New countries, survey instruments or later periods need external validation. Monitor input/missingness drift and error by country when new labelled data arrive; retrain and version only after that evaluation.

EVS/WVS (2024), Joint EVS/WVS 2017-2022 Dataset, ZA7505 v5.0.0, doi:10.4232/1.14320. Raw respondent data, local split IDs and secrets are excluded from distribution. This repository publishes aggregate results and a trusted project model; its instructions do not require redistributing the source survey.
