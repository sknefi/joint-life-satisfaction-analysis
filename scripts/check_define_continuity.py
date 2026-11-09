#!/usr/bin/env python3
"""Complete promised Define diagnostics without changing the frozen model."""

from pathlib import Path
import hashlib
import json

import joblib
import numpy as np
import pandas as pd

from evs_model.audit_analysis import training_inference_frame
from evs_model.config import CORE
from evs_model.data import load_source, within_country_folds
from evs_model.metrics import reliability, scores
from evs_model.training import cross_validate, write_json

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / '02_develop/results'
raw = load_source(ROOT / 'data/processed/evs_v5_0.parquet')
frame, held = training_inference_frame(raw)
selection = json.loads((RESULTS / 'selection.json').read_text())
name = selection['selected']
params = next(r['parameters'] for r in selection['candidates'] if r['model'] == name)
demographic_only = ('X001', 'X003', 'X025R', 'cntry_AN')
print('Demographics-only training CV:', demographic_only, flush=True)
demographic_summary, _ = cross_validate(name, params, demographic_only, frame,
                                       within_country_folds(frame), jobs=4)

# Reuse saved training-fold predictions; the validation/test sets stay untouched.
key = hashlib.sha256(json.dumps([name, params, list(CORE), 'within'], sort_keys=True).encode()).hexdigest()[:16]
summary, oof = joblib.load(ROOT / f'02_develop/local/cv_{key}.joblib')
assert len(oof) == len(frame) and not set(frame.cntry_AN) & set(held)
assert abs(scores(frame.A170, oof)['mae'] - np.mean([r['mae'] for r in summary['folds']])) < .002
calibration = []
for country, positions in frame.groupby('cntry_AN').indices.items():
    for row in reliability(frame.A170.iloc[positions], oof[positions]):
        calibration.append({'country': country, **row, 'sparse_bin': row['n'] < 30})
pd.DataFrame(calibration).to_csv(RESULTS / 'calibration_country_cv.csv', index=False)

def distribution(mask, weight):
    y = frame.loc[mask, 'A170'].to_numpy(dtype=int)
    w = np.asarray(weight)[np.asarray(mask)]
    counts = np.bincount(y, minlength=11)[1:11]
    mass = np.bincount(y, weights=w, minlength=11)[1:11]
    if not len(y) or not w.sum():
        return counts, None, 0.
    probabilities = mass / mass.sum()
    assert np.isclose(probabilities.sum(), 1) and (probabilities >= 0).all()
    return counts, probabilities, float(w.sum()**2 / np.square(w).sum())

gw = frame.analysis_weight.to_numpy()
equal = gw * frame.wght_eq1000.to_numpy()
groups = [('overall', 'training_sample', np.ones(len(frame), dtype=bool), equal)]
for country in sorted(frame.cntry_AN.unique()):
    mask = frame.cntry_AN.eq(country).to_numpy()
    groups.append(('country', country, mask, gw))
    for variable, levels in (('X047E_EVS5', range(1, 11)), ('X028', range(1, 9))):
        for level in levels:
            groups.append((f'country_{variable}', f'{country}:{level}', mask & frame[variable].eq(level).to_numpy(), gw))
for variable, levels in (('X047E_EVS5', range(1, 11)), ('X028', range(1, 9))):
    for level in levels:
        groups.append((variable, str(level), frame[variable].eq(level).to_numpy(), equal))
for label, mask in [('income_low_1_2', frame.X047E_EVS5.isin([1,2])),
                    ('income_high_9_10', frame.X047E_EVS5.isin([9,10])),
                    ('paid_employment', frame.X028.isin([1,2])),
                    ('unemployed', frame.X028.eq(7))]:
    groups.append(('contrast_group', label, mask.to_numpy(), equal))
distributions, summaries = [], []
for kind, value, mask, weights in groups:
    counts, probabilities, effective = distribution(mask, weights)
    n = int(counts.sum())
    suppressed = n < 30 or effective < 30
    for score in range(1, 11):
        distributions.append({'kind': kind, 'value': value, 'score': score,
            'n_group': n, 'n_score': int(counts[score-1]), 'effective_n': effective,
            'raw_proportion': None if suppressed else float(counts[score-1]/n),
            'weighted_proportion': None if suppressed else float(probabilities[score-1]),
            'suppressed': suppressed})
    if not suppressed:
        median = int(np.searchsorted(probabilities.cumsum(), .5) + 1)
        row = {'kind': kind, 'value': value, 'n': n, 'effective_n': effective,
               'p_at_least_7': float(probabilities[6:].sum()),
               'p_at_least_8': float(probabilities[7:].sum()), 'weighted_median': median}
        assert row['p_at_least_8'] <= row['p_at_least_7'] + 1e-12
        summaries.append(row)
pd.DataFrame(distributions).to_csv(RESULTS / 'group_ordinal_distributions.csv', index=False)
pd.DataFrame(summaries).to_csv(RESULTS / 'threshold_sensitivity.csv', index=False)
lookup = {r['value']: r for r in summaries if r['kind'] == 'contrast_group'}
contrasts = []
for label, high, low in [('income_high_minus_low', 'income_high_9_10', 'income_low_1_2'),
                          ('paid_minus_unemployed', 'paid_employment', 'unemployed')]:
    a, b = lookup[high], lookup[low]
    contrasts.append({'contrast': label,
        'gap_threshold_7': a['p_at_least_7'] - b['p_at_least_7'],
        'gap_threshold_8': a['p_at_least_8'] - b['p_at_least_8'],
        'median_high_group': a['weighted_median'], 'median_low_group': b['weighted_median']})
write_json(RESULTS / 'define_continuity.json', {
    'analysis_partition': 'train only', 'n': len(frame), 'countries': 30,
    'demographics_only_features': list(demographic_only),
    'demographics_only_cv': demographic_summary,
    'calibration_countries': len(set(r['country'] for r in calibration)),
    'group_distribution_rows': len(distributions), 'contrasts': contrasts,
    'limitations': 'Threshold/median comparisons are descriptive sensitivity checks, not new causal claims or uncertainty intervals; country CV calibration is a tuned-training diagnostic.',
    'frozen_model_reselected': False, 'final_tests_evaluated': False})
print(json.dumps({'demographic_mae': demographic_summary['mae'], 'contrasts': contrasts}), flush=True)
