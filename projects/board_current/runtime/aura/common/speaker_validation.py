"""Open-set score evaluation. Calibration and held-out trials stay separate."""
import math


def metrics(trials, threshold, margin):
    if not math.isfinite(threshold) or not -1 <= threshold <= 1 or not math.isfinite(margin) or not 0 <= margin <= 2:
        raise ValueError('Invalid operating point')
    known = unknown = correct = wrong = rejected = false_accept = 0
    for trial in trials:
        scores = trial['scores']
        if not scores or not all(isinstance(k, str) and k and type(v) in (int,float)
                                 and math.isfinite(v) and -1 <= v <= 1 for k,v in scores.items()):
            raise ValueError('Invalid gallery scores')
        ranked = sorted(((v,k) for k,v in scores.items()), reverse=True)
        accepted = ranked[0][0] >= threshold and (len(ranked) == 1 or ranked[0][0]-ranked[1][0] >= margin)
        truth = trial['identity_id']
        if truth in scores:
            known += 1
            if not accepted: rejected += 1
            elif ranked[0][1] == truth: correct += 1
            else: wrong += 1
        else:
            unknown += 1
            false_accept += int(accepted)
    return {'known_trials': known, 'unknown_trials': unknown, 'correct_known': correct,
            'wrong_known': wrong, 'rejected_known': rejected, 'false_accept_unknown': false_accept,
            'unknown_false_accept_rate': false_accept/unknown if unknown else None,
            'known_rejection_rate': rejected/known if known else None,
            'known_wrong_identity_rate': wrong/known if known else None}


def calibrate(trials, thresholds, margins, maximum_false_accept_rate):
    if not trials or not 0 <= maximum_false_accept_rate <= 1:
        raise ValueError('Invalid calibration trials/target')
    candidates = []
    for threshold in thresholds:
        for margin in margins:
            result = metrics(trials, threshold, margin)
            if not result['known_trials'] or not result['unknown_trials']:
                raise ValueError('Need enrolled and unenrolled people in calibration')
            if (result['unknown_false_accept_rate'] <= maximum_false_accept_rate
                    and result['wrong_known'] == 0 and result['correct_known'] > 0):
                candidates.append((result['correct_known'], threshold, margin, result))
    if not candidates:
        return {'state': 'NO_OPERATING_POINT', 'field_calibrated': False}
    _, threshold, margin, result = max(candidates, key=lambda x: (x[0], x[1], x[2]))
    return {'state': 'CANDIDATE_ONLY', 'threshold': threshold, 'margin': margin,
            'field_calibrated': False, 'calibration_metrics': result,
            'note': 'Finite sample rates are estimates; zero observed errors is not a guarantee.'}


def validate_trial_partitions(calibration, held_out):
    """Opaque capture IDs and global recording-session IDs must be disjoint."""
    for rows in (calibration, held_out):
        if not rows:
            raise ValueError('Both calibration and held-out sets are required')
        if any(not row.get('session_id') or not row.get('pcm_sha256') for row in rows):
            raise ValueError('Missing recording provenance')
        if len({row['pcm_sha256'] for row in rows}) != len(rows):
            raise ValueError('Repeated audio in trials')
    for key in ('session_id', 'pcm_sha256'):
        if {r[key] for r in calibration} & {r[key] for r in held_out}:
            raise ValueError('Calibration/held-out leakage: '+key)
