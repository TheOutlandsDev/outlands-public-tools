"""Installed four-tool exercise using only embedded fictional fixtures."""
import json
from importlib.resources import files
from outlands_probability_vector_checker import vectors
from outlands_binary_probability_error_calculator import errors
from outlands_reliability_bin_reporter import bins
from outlands_calibration_map_checker import maps


def example(package, name='input.json'):
    return json.loads(files(package).joinpath('examples', name).read_text(encoding='utf-8'))


def encoded(value):
    return (json.dumps(value, sort_keys=True, separators=(',', ':')) + '\n').encode('ascii')


def exercise():
    vector_input = example('outlands_probability_vector_checker')
    vector_report = vectors.check(encoded(vector_input))
    assert vector_report['assessment']['all_vectors_valid']
    assert vector_report['assessment']['valid_cases'] == 4
    error_input = example('outlands_binary_probability_error_calculator')
    contract = error_input['contract']
    by_case = {row['id']: row for row in vector_input['cases']}
    for row in error_input['predictions']:
        source = by_case[row['case']]
        assert source['model'] == contract['model'] and source['model_revision'] == contract['model_revision']
        row['probability'] = next(p['value'] for p in source['probabilities'] if p['label'] == contract['positive_label'])
    error_report = errors.check(encoded(error_input))
    assert error_report['metrics']['total_squared_error']['exact_fraction'] == '3/8'
    assert error_report['metrics']['mean_squared_error']['exact_fraction'] == '3/32'
    bin_input = example('outlands_reliability_bin_reporter')
    for key in ('contract', 'cohort', 'predictions', 'outcomes'):
        bin_input[key] = error_input[key]
    bin_report = bins.check(encoded(bin_input))
    for key in ('contract_sha256', 'cohort_sha256', 'predictions_sha256', 'outcomes_sha256'):
        assert bin_report[key] == error_report[key]
    assert bin_report['metrics']['weighted_absolute_bin_gap']['exact_fraction'] == '1/4'
    assert sum(row['cases'] for row in bin_report['metrics']['bins']) == 4
    map_input = example('outlands_calibration_map_checker', 'needs-review.json')
    map_report = maps.check(encoded(map_input))
    assert map_report['status'] == 'REVIEW_REQUIRED'
    assert map_report['assessment']['points_changed'] == ['point-middle']
    assert map_report['map_assessments']['after']['nondecreasing']
    assert not map_report['mapping_applied']
    for report in (vector_report, error_report, bin_report, map_report):
        for key in ('calibration_established', 'cohort_independence_verified', 'label_truth_verified',
                    'model_fitted', 'model_updated', 'inference_performed', 'target_changes_performed'):
            assert report[key] is False
    error_input['outcomes'].pop()
    assert errors.check(encoded(error_input))['metrics'] is None
    assert bins.check(encoded(bin_input))['metrics'] is None
    return {'status': 'PASS', 'fictional_cases': 4, 'total_squared_error': '3/8',
            'mean_squared_error': '3/32', 'weighted_absolute_bin_gap': '1/4',
            'map_change': 'REVIEW_REQUIRED', 'missing_outcome_metrics': None}


if __name__ == '__main__':
    print(json.dumps(exercise(), sort_keys=True))
