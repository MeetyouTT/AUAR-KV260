"""Evaluate model-labelled scores without changing any running threshold."""
import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common.speaker_validation import calibrate, metrics, validate_trial_partitions


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input', type=Path)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--maximum-false-accept-rate', type=float, default=0.01)
    args = parser.parse_args()
    data = json.loads(args.input.read_text(encoding='utf-8'))
    if not data.get('model_id') or not data.get('enrollment_pcm_sha256') or not data.get('enrollment_session_ids'):
        raise ValueError('Need model and enrollment provenance')
    calibration, held_out = data['calibration'], data['held_out']
    validate_trial_partitions(calibration, held_out)
    gallery = set(calibration[0]['scores'])
    if any(set(r['scores']) != gallery for r in calibration+held_out):
        raise ValueError('Gallery differs across trials')
    if any(r['pcm_sha256'] in data['enrollment_pcm_sha256'] or r['session_id'] in data['enrollment_session_ids']
           for r in calibration+held_out):
        raise ValueError('Enrollment/query leakage')
    result = calibrate(calibration, data['thresholds'], data['margins'], args.maximum_false_accept_rate)
    if result['state'] == 'CANDIDATE_ONLY':
        result['held_out_metrics'] = metrics(held_out, result['threshold'], result['margin'])
        held_metrics = result['held_out_metrics']
        result['held_out_meets_false_accept_target'] = bool(
            held_metrics['known_trials'] and held_metrics['unknown_trials']
            and held_metrics['unknown_false_accept_rate'] <= args.maximum_false_accept_rate
            and held_metrics['wrong_known'] == 0 and held_metrics['correct_known'] > 0)
    result['model_id'] = data['model_id']
    args.output.write_text(json.dumps(result, indent=2), encoding='utf-8')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
