#!/usr/bin/env python3
"""Render concise Develop reports from the protocol and saved computed results."""

from __future__ import annotations

import argparse
import json
from html import escape
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import Image, KeepTogether, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

ROOT = Path(__file__).resolve().parents[1]
NAVY = colors.HexColor("#15324A")
TEAL = colors.HexColor("#168C8C")
INK = colors.HexColor("#23313B")
PALE = colors.HexColor("#F0F6F7")
STYLES = {
    "body": ParagraphStyle("body", fontName="Helvetica", fontSize=8.8, leading=12, textColor=INK, spaceAfter=7),
    "small": ParagraphStyle("small", fontName="Helvetica", fontSize=7.2, leading=9.5, textColor=INK, spaceAfter=5),
    "heading": ParagraphStyle("heading", fontName="Helvetica-Bold", fontSize=10.5, leading=13, textColor=NAVY, spaceBefore=8, spaceAfter=6, keepWithNext=True),
    "cell": ParagraphStyle("cell", fontName="Helvetica", fontSize=7.2, leading=9.4, textColor=INK),
    "headcell": ParagraphStyle("headcell", fontName="Helvetica-Bold", fontSize=7.4, leading=9.5, textColor=colors.white),
    "code": ParagraphStyle("code", fontName="Courier", fontSize=7.2, leading=10, textColor=NAVY, backColor=PALE, borderPadding=6, spaceAfter=10),
}


def body(text, small=False):
    return ("p", text, "small" if small else "body")


def heading(text):
    return ("h", text)


def table(headers, rows, widths=None):
    return ("table", headers, rows, widths)


def read(name):
    return json.loads((ROOT / "02_develop/results" / name).read_text())


def render(part, subtitle, pages):
    output = ROOT / "02_develop/output" / f"filip_karika_model_development_report_part_{part}.pdf"
    output.parent.mkdir(parents=True, exist_ok=True)
    story, markdown = [], [f"# Model Development Report - Part {part}: {subtitle}\n"]
    width = A4[0] - 72
    for index, page in enumerate(pages):
        if index:
            story.append(PageBreak())
        for block in page:
            if block[0] == "h":
                story.append(Paragraph(block[1], STYLES["heading"]))
                markdown.append("\n## " + block[1])
            elif block[0] == "p":
                story.append(Paragraph(block[1], STYLES[block[2]]))
                markdown.append(block[1])
            elif block[0] == "code":
                story.append(Paragraph(escape(block[1]).replace("\n", "<br/>"), STYLES["code"]))
                markdown.append("```text\n" + block[1] + "\n```")
            elif block[0] == "image":
                story.append(Image(str(block[1]), width=block[2], height=block[3], hAlign="CENTER"))
                markdown.append(f"![{block[4]}](../figures/{Path(block[1]).name})")
            else:
                _, headers, rows, widths = block
                widths = [width * v for v in widths] if widths else [width / len(headers)] * len(headers)
                cells = [[Paragraph(str(value), STYLES["headcell"]) for value in headers]]
                cells.extend([[Paragraph(str(value), STYLES["cell"]) for value in row] for row in rows])
                grid = Table(cells, colWidths=widths, repeatRows=1, hAlign="LEFT")
                grid.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), NAVY), ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [PALE, colors.white]), ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
                    ("TOPPADDING", (0, 0), (-1, -1), 7), ("LEFTPADDING", (0, 0), (-1, -1), 7),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 7), ("LINEBELOW", (0, 0), (-1, 0), 1, TEAL)]))
                story.extend((grid, Spacer(1, 8)))
                markdown.extend(("| " + " | ".join(headers) + " |", "|" + "---|" * len(headers)))
                markdown.extend("| " + " | ".join(str(v).replace("\n", " ") for v in row) + " |" for row in rows)

    def decorate(canvas, doc):
        w, h = A4
        canvas.saveState()
        canvas.setFillColor(NAVY)
        canvas.rect(36, h - 83, w - 72, 51, fill=True, stroke=False)
        canvas.setFillColor(colors.white)
        canvas.setFont("Helvetica-Bold", 13)
        canvas.drawString(47, h - 51, f"Model Development Report - Part {part}")
        canvas.setFont("Helvetica", 9)
        canvas.drawString(47, h - 66, subtitle)
        canvas.setFillColor(TEAL)
        canvas.rect(36, h - 86, w - 72, 3, fill=True, stroke=False)
        canvas.setFillColor(colors.HexColor("#60717C"))
        canvas.setFont("Helvetica", 6.5)
        canvas.drawString(36, 25, "Filip Karika | 4EK481 / 4EK666 | Winter semester 2026 | EVS 2017-2021")
        canvas.drawRightString(w - 36, 25, f"Page {doc.page}")
        canvas.restoreState()

    doc = SimpleDocTemplate(str(output), pagesize=A4, leftMargin=36, rightMargin=36,
                            topMargin=100, bottomMargin=42, title=f"Model Development Part {part}: {subtitle}", author="Filip Karika")
    doc.build(story, onFirstPage=decorate, onLaterPages=decorate)
    from pypdf import PdfReader
    actual = len(PdfReader(output).pages)
    if actual != len(pages):
        raise RuntimeError(f"Part {part}: expected {len(pages)} pages, got {actual}; repair layout.")
    source = ROOT / "02_develop/report" / f"model_development_report_part_{part}.md"
    source.write_text("\n\n".join(markdown) + "\n")
    print(f"Created {output} ({actual} pages)")


def part_one():
    pages = [[
        heading("1. Questions, candidates and commitments"),
        body("<b>Data and scope.</b> Joint EVS/WVS 2017-2022 v5.0.0, EVS records only (study = 1): 59,438 respondents in 36 countries, fieldwork 2017-2021. One row is one person; this is a clustered pooled cross-section, not a longitudinal panel. The response is A170, ordinal life satisfaction 1-10."),
        table(["Question / goal", "Approach and rationale", "Critical assumption"], [
            ["Prediction: an unseen EVS-style respondent in a represented country", "Empirical median/frequency baseline; regularized ordinal logistic; random forest; histogram gradient boosting", "Inputs known after the non-target questionnaire; relationships and measurement transfer to unseen respondents."],
            ["Inference: population proportions with A170 >= 7, and income/employment gaps", "Country-specific weighted ratios; equal-country pooling; population-size-weighted sensitivity; approximate bootstrap uncertainty", "Survey weights adequately adjust observed margins; residual selection and within-country dependence remain limitations."],
            ["Causality: effect of obtaining paid work among initially unemployed adults", "Not identified by EVS; propose a prospective panel / target trial with pre-employment adjustment", "Temporal ordering, pre-treatment common causes, overlap, consistency and no material spillovers."],
        ], [.22, .44, .34]),
        heading("2. Prediction case and information available"),
        body("Predict after an EVS-style respondent has answered the non-target questions, before A170 is observed. Intended use is a research demonstration and possible future imputation research, conditional on validation. It is not an intervention recommendation or a claim about present-day populations."),
        body("<b>Core inputs:</b> X001 sex; X003 age; X025R education; X028 employment; X047E_EVS5 household-income decile; A009 health; A165 trust; A173 control; cntry_AN country. Exclude IDs, weights, fieldwork dates, year and interview mode from the primary model. A008 happiness is a separate near-proxy sensitivity analysis; a demographic/economic-only specification tests dependence on subjective items."),
        body("<b>Representation:</b> age and age squared, median-imputed within each training fold, standardized using that fold; a missing-age indicator. Other survey codes are explicitly one-hot encoded, including a missing category. Category codes are not assumed to be equally spaced. Age 82 denotes 82+. The raw CSV and its negative missing codes remain immutable."),
        heading("3. Frozen evaluation protocol"),
        body("Seed 42 selects six countries using country labels only for a final transfer test. In the remaining 30, valid-target respondents are partitioned within country x outcome strata: approximately 70% training, 10% production validation, 20% final same-country test. Rounding is documented. Missing targets are excluded from prediction fitting; missing predictors do not cause complete-case deletion."),
        body("Five-fold within-country CV tunes candidates on training data only. Five-fold country-group CV of the frozen candidate configurations checks transfer within the training countries. Preprocessing is refitted inside every fold. Production validation is opened only after the winner is frozen. Both final prediction tests are reserved for Assure."),
    ], [
        heading("4. Candidate assumptions, objectives and possible failures"),
        table(["Candidate", "Assumptions and consequences", "Repair / verdict"], [
            ["Baseline", "Training outcome frequencies transfer. A global median ignores country and individual variation: potentially high bias, low variance.", "Mandatory benchmark; assumptions plausible only as a reference."],
            ["Ordinal logistic (all-threshold, L2)", "One additive latent score with ordered logistic thresholds; shared slopes across thresholds. Missed nonlinearities/interactions or threshold-specific effects create bias. L2 reduces variance; probabilities need calibration checks.", "Quadratic age and explicit categories; tune L2. Violations may be harmful; compare with flexible candidates."],
            ["Random forest classifier", "Enough observations support local partitions and interactions. Sparse subgroups and deep trees increase variance; leaf averaging can flatten extremes. Classifier does not exploit outcome order during fitting.", "Limit depth, impose substantial leaf sizes, average 200 trees; judge on ordinal-aware metrics. Assumptions plausible with regularization."],
            ["Histogram gradient boosting classifier", "Useful signal can be approximated by shallow interactions. Sequential fitting can overfit noise; nominal multiclass loss does not encode score distance. No reliable extrapolation to new contexts.", "Small learning rates and trees, regularization and fold-local early stopping. Plausible, with careful tuning and group validation."],
        ], [.21, .48, .31]),
        body("<b>Objectives:</b> baseline median minimizes empirical absolute error; its probabilities are empirical frequencies. The ordinal estimator minimizes the sum of nine binary threshold logistic losses plus alpha/2 times squared coefficient norm (an all-threshold surrogate, not exact categorical ordered-logit likelihood). Forests greedily reduce Gini impurity. Boosting minimizes multiclass log loss through successive trees."),
        body("<b>Alternative criterion:</b> refit the selected forest configuration with Shannon entropy instead of Gini. Keep its other hyperparameters fixed to isolate the criterion change. This compares local split objectives, not two globally optimized forest likelihoods. Evaluate probability and point-prediction differences out of fold."),
        heading("5. Tuning, success and expected ranking"),
        body("Initial search: ordinal alpha {0.1, 1, 10, 100}; forest 200 trees, depth {6,10}, minimum leaf {20,50}, max_features {sqrt,0.7}; boosting eight seeded combinations of learning_rate {0.05,0.1}, leaves {7,15}, minimum leaf {50,100}, L2 {0,1}; up to 200 iterations. A pre-specified one-step outward extension follows boundary optima. Tree extension changes depth/leaf-size together as a bounded sensitivity, not an exhaustive expanded grid."),
        body("<b>Selection:</b> minimize mean CV MAE of the predicted distribution's median; break exact metric ties using RPS. Prefer ordinal if within one standard error of the best candidate. Retain baseline if no model improves it. Report log loss, normalized ranked probability score (RPS), Brier score for A170 >= 7, calibration and subgroup error. Probabilities are estimated distributions, not a confidence interval for an individual's outcome."),
        body("<b>Expectation:</b> boosting may win through nonlinear health/control/income interactions; ordinal may be competitive because self-report noise limits useful complexity; forest may be more conservative. Similar CV errors, poor calibration, or worse country transfer would change this ranking. No performance claim is made before fitting."),
    ], [
        heading("6. Inference: estimand, weighting and uncertainty"),
        body("Estimate country-specific proportions of A170 scores 7-10 and marginal income/employment differences among adults in private households represented by the 36 EVS country surveys during 2017-2021. Within-country estimates use gwght. Primary pooled ratios use gwght x wght_eq1000 (equal-country-size scaling); sensitivity ratios use gwght x pwght (population-size scaling). Unweighted results describe the observed sample. Finite differences in national gwght totals mean the first pooled ratio is not an exactly equally normalized average of 36 country means."),
        body("Pre-specify income contrast deciles 9-10 minus 1-2; employment contrast paid full/part-time work (X028=1/2) minus unemployment (X028=7). These are descriptive associations, not adjusted causal effects. Report counts, Kish effective sample size and approximate 95% intervals. Suppress estimates with raw or effective n below 30."),
        body("Use 1,000 respondent bootstrap draws separately within each fixed country, recalculating weighted ratios and contrasts. The common file has no definitive PSU/stratum identifiers. These intervals therefore approximate conditional sampling variability under iid respondents within country; they can be too narrow under unobserved cluster dependence and are not full survey-design intervals. Do not cluster a national estimate on its sole country."),
        body("Income missingness is 14.70% and potentially MNAR. Compare observed-income and missing-income respondents, report country/group coverage, and avoid claiming that complete-case ratios or survey weights remove this bias. More respondents reduce variance but do not eliminate nonresponse, measurement or selection bias. Self-report, translations and modes can change the measured construct across countries."),
        heading("7. Causality: identification before estimation"),
        body("The question remains: among adults 18-64 unemployed at baseline, what is the average effect on A170 at 12 months of entering paid employment within three months versus remaining unemployed? EVS observes current employment and current satisfaction once; neither transition timing nor baseline satisfaction is available."),
        body("Prior well-being, health, job history, household circumstances and labour-market opportunities influence both employment and satisfaction. Reverse causation is plausible. Current income may mediate employment's effect and should not automatically be controlled when targeting a total effect. Cross-sectional regression or feature importance does not identify this intervention."),
        body("<b>Proposed repair:</b> follow baseline-unemployed adults prospectively, measure pre-treatment common causes and well-being, record job entry and quality, and pre-specify a target trial. With defensible conditional exchangeability, overlap and consistency, use doubly robust outcome/propensity adjustment with cross-fitting and appropriate dependence-aware uncertainty. Check overlap, balance, attrition and spillovers. A randomized job-placement offer identifies the offer effect, not automatically employment's effect."),
        body("<b>Verdict:</b> the causal effect is not identified from the supplied EVS cross-section. Part II will report descriptive employment associations with qualified uncertainty, but no fabricated treatment effect or causal standard error."),
        heading("8. Reproduction and references"),
        body("The implementation will preserve source hashes, split manifests locally, seeds, versions, configurations, optimizer diagnostics and all report-generating aggregates. Final prediction-test scores will not appear in Develop. Part III will be an installable GitHub repository, with no web hosting or deployment."),
        body('EVS/WVS (2024), Joint EVS/WVS 2017-2022, ZA7505 v5.0.0, <link href="https://doi.org/10.4232/1.14320" color="#168C8C">doi:10.4232/1.14320</link>. Variable Report, June 2024: supports, missing codes, weighting and anonymisation. Rennie &amp; Srebro (2005), Loss Functions for Preference Levels. scikit-learn documentation: RandomForestClassifier and HistGradientBoostingClassifier. Source: <link href="https://github.com/sknefi/joint-life-satisfaction-analysis" color="#168C8C">github.com/sknefi/joint-life-satisfaction-analysis</link>.', True),
    ]]
    render(1, "Candidates and Assumptions | Life satisfaction across EVS countries", pages)


def part_two():
    selection, splits, run = read("selection.json"), read("splits.json"), read("run.json")
    alt, sensitivity, inference = read("alternative_criterion.json"), read("sensitivity.json"), read("inference.json")
    grouped, counts = read("country_cv.json"), splits["counts"]
    candidates = selection["candidates"]
    rows = []
    for c in candidates:
        diag = read(c["model"] + "_parameters.json")
        fitted = "Empirical frequencies" if c["model"] == "baseline" else (
            f"{diag['expanded_features']} coefficients + 9 cutpoints" if c["model"] == "ordinal" else f"{diag['trees']} trees")
        if c["model"] == "baseline":
            objective, tuning, optimizer = "Empirical absolute loss / frequencies", "None", "Closed form"
        elif c["model"] == "ordinal":
            objective, tuning, optimizer = "Threshold logistic + L2", f"alpha={c['parameters']['alpha']}", "L-BFGS-B; analytic gradient"
        elif c["model"] == "forest":
            p = c["parameters"]
            objective, tuning, optimizer = "Gini split gain", f"depth {p['max_depth']}; leaf {p['min_samples_leaf']}; mtry {p['max_features']}", "Greedy CART; seed 42"
        else:
            p = c["parameters"]
            objective, tuning, optimizer = "Multiclass log loss", f"lr {p['learning_rate']}; leaves {p['max_leaf_nodes']}; leaf {p['min_samples_leaf']}; L2 {p['l2_regularization']}", "Histogram boosting; early stop"
        rows.append([c["model"], objective, fitted, tuning, optimizer, f"{c['mae']:.3f} +/- {c['mae_se']:.3f}<br/>{c['log_loss']:.3f}<br/>{c['rps']:.4f}"])
    pages = [[
        heading("1. Training results: validation inside training only"),
        body(f"EVS subset: 59,438 respondents / 36 countries; A170 has 59,122 valid responses. The fixed split yields {counts['train']:,} training, {counts['production_validation']:,} production-validation, {counts['same_country_test']:,} same-country final-test and {counts['country_test']:,} held-out-country final-test cases. The 316 missing targets are excluded from predictive learning. Counts differ slightly from nominal percentages due to per-stratum rounding."),
        body("Held-out countries: " + ", ".join(splits["held_out_countries"]) + ". Neither final prediction test was used for tuning or model comparison. Five within-country folds share country contexts but not respondents; five group folds remove entire training-country contexts."),
        table(["Approach", "Criterion", "Fitted summary", "Chosen tuning", "Optimizer", "CV MAE +/- SE<br/>Log loss<br/>RPS"], rows, [.11, .16, .16, .22, .17, .18]),
        body(f"<b>Frozen selection:</b> {selection['selected']}; rule: {selection['rule']}. MAE uses the median of the predicted 10-category distribution. SE is the sample SD of five fold MAEs divided by sqrt(5): a descriptive tuning uncertainty, not a survey-design or independent-fold confidence interval."),
        heading("2. Criteria and representation"),
        body("Ordinal fitting minimizes all-threshold logistic surrogate loss plus L2; the baseline uses observed frequencies. Forests greedily improve Gini impurity; histogram boosting minimizes multinomial log loss. Final selection instead targets CV MAE; log loss and RPS check probability quality. No class balancing is applied, because it would change the learned prevalence. All predictive fitting is unweighted; survey-weighted inference answers a separate population question."),
        body("Age and age squared use fold-specific median imputation and scaling; a missing-age indicator is added. Nominal and ordinal survey items use explicit categories, including missingness. Country holdouts receive unknown-country indicator blocks during group CV; the public command rejects unsupported countries. The production artifact contains only 30 training-country contexts."),
        heading("3. Alternative split criterion"),
        table(["Fixed forest settings; changed criterion", "CV MAE", "Log loss", "RPS"], [
            ["Gini", f"{alt['primary']['mae']:.4f}", f"{alt['primary']['log_loss']:.4f}", f"{alt['primary']['rps']:.5f}"],
            ["Shannon entropy", f"{alt['alternative']['mae']:.4f}", f"{alt['alternative']['log_loss']:.4f}", f"{alt['alternative']['rps']:.5f}"],
        ], [.43, .19, .19, .19]),
        body(f"Changing only the criterion changes CV MAE by {alt['alternative']['mae'] - alt['primary']['mae']:+.4f}. This is a controlled comparison of greedy split objectives; it is not evidence that the forest finds a global likelihood optimum. Probability and point-score changes are both reported."),
    ], [
        heading("4. Search, chosen hyperparameters and sensitivity"),
        table(["Candidate", "Selected hyperparameters"], [[c["model"], escape(json.dumps(c["parameters"], sort_keys=True))] for c in candidates], [.2, .8]),
        body("Initial search and one-step boundary extensions follow Part I. Every candidate uses five folds and identical split indices; no preprocessing is shared across folds. Forest size is fixed at 200 trees. Boosting uses at most 200 iterations, a 15% internal training-fold validation fraction, patience 15, and seed 42. Complete trial spaces, fold results and timings are in results/trials.json."),
        table(["Frozen selected-family specification", "CV MAE", "Log loss", "RPS"], [[s["specification"], f"{s['mae']:.3f}", f"{s['log_loss']:.3f}", f"{s['rps']:.4f}"] for s in sensitivity], [.43, .19, .19, .19]),
        body("Sensitivity fits reuse the selected family's hyperparameters without retuning; differences assess predictor availability, not separately optimized competitors. Adding happiness tests near-proxy dependence; removing subjective inputs tests whether survey-like subjective answers are essential."),
        ("image", ROOT / "02_develop/figures/cv_curve.png", 480, 195, "Training-only CV curve"),
        heading("5. Optimization and fitted parameters"),
        body(optimizer_text()),
        body("Forests use greedy CART and bootstrap aggregation; there is no continuous gradient convergence test. Boosting uses greedy histogram trees with early stopping, which is part of regularization rather than a certificate of global optimality. A second seed is reported for the chosen tree configurations as an optimizer/randomization stability check. Full settings, thresholds, coefficients, tree counts and diagnostics are saved as JSON; fitted estimators are serialized separately."),
    ], [
        heading("6. Transfer diagnostics and uncertainty"),
        table(["Frozen candidate", "Grouped CV MAE", "Log loss", "RPS"], [[g["model"], f"{g['mae']:.3f}", f"{g['log_loss']:.3f}", f"{g['rps']:.4f}"] for g in grouped], [.3, .28, .21, .21]),
        body("Group CV is a secondary training-country diagnostic, not nested CV or a score on the six held-out test countries: configurations were chosen using within-country CV across the training sample. It exposes transfer to unfamiliar country indicator blocks. Country/subgroup errors and reliability bins are provided as aggregates. Predicted category probabilities express model uncertainty; no individual prediction intervals are claimed."),
        heading("7. Population estimates and descriptive gaps"),
        table(["Overall weighting", "High-satisfaction proportion", "Approx. SE", "Approx. 95% interval"], [[r["value"], f"{100*r['estimate']:.2f}%", f"{100*r['standard_error']:.2f} pp", f"{100*r['ci_low']:.2f}-{100*r['ci_high']:.2f}%"] for r in inference["overall"]], [.26, .27, .2, .27]),
        table(["Descriptive contrast", "Difference", "Approx. SE", "Approx. 95% interval"], [[r["contrast"].replace("_", " "), f"{100*r['estimate']:+.2f} pp", f"{100*r['standard_error']:.2f} pp", f"{100*r['ci_low']:+.2f} to {100*r['ci_high']:+.2f} pp"] for r in inference["contrasts"]], [.36, .16, .18, .3]),
        body("These pre-specified inferential descriptions use all 36 country samples separately from predictive model selection. Within-country gwght adjusts observed margins; pooled equal-country-size and population-size weighting target different summaries. Intervals use 1,000 iid respondent bootstraps within fixed countries. They omit unobserved PSU dependence, do not estimate uncertainty over a hypothetical population of countries, and do not remove selection or measurement bias. Small or low-effective-size groups are suppressed."),
        body(income_text()),
        heading("8. Causality, reproducibility and remaining evaluation"),
        body("The paid-employment gap above is an association. The effect of obtaining employment remains unidentified: no pre-employment well-being, transition assignment or 12-month outcome is observed. No causal coefficient or causal standard error is reported. The prospective design and assumptions in Part I remain required."),
        body(f"Environment: Python {run['versions']['python']}; scikit-learn {run['versions']['scikit-learn']}; NumPy {run['versions']['numpy']}; SciPy {run['versions']['scipy']}. Seed 42. Input Parquet SHA-256: {run['source_sha256'][:20]}... Full source/code hashes, package versions, split policy and optimizer settings are recorded. Source: EVS/WVS ZA7505 v5.0.0, doi:10.4232/1.14320. Reproduce with make train, make inference and make develop-reports.", True),
    ]]
    render(2, "Training and Tuning | Objectives, validation and uncertainty", pages)


def optimizer_text():
    o = read("ordinal_parameters.json")
    b = read("boosting_parameters.json")
    stability_path = ROOT / "02_develop/results/seed_stability.json"
    extra = ""
    if stability_path.exists():
        s = read("seed_stability.json")
        extra = " Alternate-seed details are recorded in seed_stability.json."
    return (f"<b>Ordinal:</b> L-BFGS-B with analytic gradients, ordered-threshold increment constraints, maximum 2,000 initial iterations, initial ftol=1e-9; retry at stricter tolerance when necessary. Final fit: {o['iterations']} iterations; success={o['success']}; objective {o['objective']:.2f}; projected gradient per training row {o['projected_gradient_per_row']:.2g}. "
            f"<b>Boosting:</b> final fit {b['iterations']} iterations / {b['trees']} trees; internal validation log loss {b['validation_loss_initial']:.4f} to {b['validation_loss_final']:.4f}." + extra)


def income_text():
    s = read("income_sensitivity.json")
    return (f"Income is missing in 14.70% of EVS rows. Equal-country-size-weighted high-satisfaction proportions are {100*s['income_observed']['estimate']:.2f}% with observed income and {100*s['income_missing']['estimate']:.2f}% with missing income. This diagnoses a potentially selected complete-case population; it does not identify an MNAR correction.")


def part_three():
    selected = read("selection.json")
    prod = read("production_validation.json")
    qa = read("production_checks.json")
    pages = [[
        heading("1. Product and intended user"),
        body(f"An installable, versioned Python repository for students/researchers reproducing EVS life-satisfaction analysis or predicting an omitted A170 response for an EVS-style respondent. Version 0.1.0 includes the frozen {selected['selected']} model and its complete preprocessing. There is no hosted service or deployment. Repository: <link href='https://github.com/sknefi/joint-life-satisfaction-analysis' color='#168C8C'>github.com/sknefi/joint-life-satisfaction-analysis</link>."),
        heading("2. Install and run"),
        ("code", "python3.12 -m venv .venv\nsource .venv/bin/activate\npython -m pip install -r requirements-lock.txt\npython -m pip install --no-deps .\nevs-predict --input examples/respondents.csv --output predictions.csv\npython -m unittest discover -s tests -p 'test_*.py'"),
        body("The model artifact lives in models/; default paths assume the repository root. Elsewhere pass --model /path/to/evs_v0_1_0.joblib. The notebook notebooks/quickstart.ipynb demonstrates synthetic profiles without requiring the respondent dataset. Source data access instructions and immutable-source rules are in data/README.md; make data, train, inference and develop-reports reproduce the analysis locally."),
        heading("3. Inputs, outputs and scope"),
        body("Input CSV columns: X001, X003, X025R, X028, X047E_EVS5, A009, A165, A173, cntry_AN. Use official survey category codes; blank values and -1..-5 become missing. Age must be 18-82, with 82 interpreted as 82+. Country is mandatory and must be one of the 30 training countries. Output: predicted_score (distribution median), probability_high_7_10 and p_1 through p_10. The predictor rejects A170, identifiers, weights, unexpected columns and invalid categories; writes are atomic."),
        heading("4. Verification as a reusable product"),
        table(["Check", "Observed result"], [
            ["Package and regression tests", f"{qa['unit_tests']} tests passed; existing profiler checks retained. Clean installed-wheel check: {qa['clean_environment_installation']}; executed notebook: {qa['notebook_executed']}."],
            ["Artifact parity", f"{qa['synthetic_cases']} synthetic cases; maximum probability difference after save/load and CLI round-trip: {qa['max_probability_difference']:.2g}. Class order and probability sums checked."],
            ["Bad inputs and leakage", "Tests cover missing codes, malformed/range/category errors, unknown countries, target exclusion, fold-local preprocessing and country isolation."],
            ["Independent production validation", f"Frozen model: n={prod['n']:,}, MAE={prod['scores']['mae']:.3f}, log loss={prod['scores']['log_loss']:.3f}, RPS={prod['scores']['rps']:.4f}. Not used to tune or select the model."],
            ["Automation and reproducibility", "GitHub Actions installs the package and runs synthetic-data tests; recorded versions, seeds, hashes and saved preprocessing. Actual hosted CI status is documented separately."],
        ], [.29, .71]),
        heading("5. Honest interpretation and maintenance"),
        body("The probabilities are model estimates for historical EVS-style contexts, not validated individual confidence intervals or causal effects. No interval coverage is claimed. Production reliability bins are saved; final same-country and six-country prediction tests remain for Assure. New countries, survey instruments or later periods need external validation. Monitor input/missingness drift and error by country when new labelled data arrive; retrain and version only after that evaluation."),
        body("EVS/WVS (2024), Joint EVS/WVS 2017-2022 Dataset, ZA7505 v5.0.0, doi:10.4232/1.14320. Raw respondent data, local split IDs and secrets are excluded from distribution. This repository publishes aggregate results and a trusted project model; its instructions do not require redistributing the source survey.", True),
    ]]
    render(3, "Production | An installable GitHub research tool", pages)


def figures():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    trials = read("trials.json")
    ordinal = sorted([t for t in trials if t["model"] == "ordinal"], key=lambda r: r["parameters"]["alpha"])
    figure, ax = plt.subplots(figsize=(8, 3.2), layout="constrained")
    ax.errorbar([t["parameters"]["alpha"] for t in ordinal], [t["mae"] for t in ordinal],
                yerr=[t["mae_se"] for t in ordinal], color="#168C8C", marker="o", capsize=4)
    ax.set_xscale("log"); ax.set_xlabel("Ordinal L2 penalty alpha (log scale)"); ax.set_ylabel("Five-fold CV MAE")
    ax.set_title("Training-only validation curve; bars show fold SE", loc="left", color="#15324A")
    ax.spines[["top", "right"]].set_visible(False)
    ax.grid(alpha=.2)
    folder = ROOT / "02_develop/figures"; folder.mkdir(exist_ok=True)
    figure.savefig(folder / "cv_curve.png", dpi=180); plt.close(figure)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--part", choices=("1", "2", "3", "all"), default="all")
    args = parser.parse_args()
    if args.part in ("1", "all"):
        part_one()
    if args.part in ("2", "all"):
        figures(); part_two()
    if args.part in ("3", "all"):
        part_three()
