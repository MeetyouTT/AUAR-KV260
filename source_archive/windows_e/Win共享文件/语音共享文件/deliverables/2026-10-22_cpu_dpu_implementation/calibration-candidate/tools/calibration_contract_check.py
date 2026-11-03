"""Pure standard-library synthetic contract check. Never hardware/model/DB.

Safe for compatibility checks independently of the production camera process.
It never imports board, numpy, cv2, xir, vart, SQLite, or transport clients.
"""
import argparse
import builtins
import hashlib
import json
from pathlib import Path
import re
import sys
import types


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument('--module', type=Path, required=True)
    parser.add_argument('--expected-sha256', required=True)
    args = parser.parse_args(argv)
    if (not args.module.is_absolute()
            or not re.fullmatch(r'[0-9a-f]{64}', args.expected_sha256)):
        raise ValueError('Explicit absolute source path and SHA256 required')
    source = args.module.read_bytes()
    actual = hashlib.sha256(source).hexdigest()
    if actual != args.expected_sha256: raise ValueError('Calibration source SHA256 mismatch')
    original_import, original_open = builtins.__import__, builtins.open
    forbidden = {'board', 'numpy', 'cv2', 'xir', 'vart', 'sqlite3', 'socket', 'urllib', 'subprocess', 'serial'}
    def guarded_import(name, *rest, **kwargs):
        if name.split('.')[0] in forbidden:
            raise AssertionError('Forbidden runtime dependency')
        return original_import(name, *rest, **kwargs)
    def no_open(*_, **__): raise AssertionError('No file I/O during contract simulation')
    module_name = '_aura_calibration_contract_'+actual[:16]
    module = types.ModuleType(module_name)
    sys.modules[module_name] = module  # Required by Python dataclass metadata.
    builtins.__import__, builtins.open = guarded_import, no_open
    checks = []
    session = None
    try:
        exec(compile(source, str(args.module), 'exec'), module.__dict__)
        assert module.calibration_configuration({}) is None
        checks.append('default_disabled')
        now = [1000]
        key = {'camera_epoch': 'synthetic', 'track_id': 1, 'track_generation': 1}
        session = module.CalibrationSession(lambda: now[0], 1000)
        axis = lambda n: tuple(1. if i == n else 0. for i in range(128))
        quality = {'yaw':0.,'roll':0.,'pixels':112.,'eye_distance':36.,'blur':100.}
        first = session.begin('calibration_gallery', 'P_A', 'C_STALE', key, key)
        ticket = session.ticket(1, now[0], key, quality=quality)
        changed = dict(key, track_generation=2)
        assert session.accept(ticket, axis(0), changed) is False
        assert session.health()['active_session'] is False
        checks.append('target_generation_invalidates')
        session.dispatch('reset', {'request_id': 'a'*32})
        try:session.dispatch('reset', {'request_id': 'a'*32})
        except ValueError:pass
        else:raise AssertionError('Mutation replay accepted')
        checks.append('mutation_replay_refused')
        assert session.suggest()['status'] == 'COVERAGE_INSUFFICIENT'
        checks.append('insufficient_coverage_explicit')
        purposes = (('calibration_gallery','P_A',0), ('calibration_gallery','P_B',1),
                    ('calibration_probe','P_A',0), ('calibration_probe','P_B',1),
                    ('calibration_unknown','P_C',2))
        for capture, (purpose, person, dimension) in enumerate(purposes):
            control = session.begin(purpose, person, 'C_'+str(capture), key, key)
            for _ in range(3):
                now[0] += 600
                ticket = session.ticket(now[0], now[0], key, quality=quality)
                assert session.accept(ticket, axis(dimension), key)
                assert not session.accept(ticket, axis(dimension), key)
            session.end(control['session_token'])
        checks.append('ticket_replay_refused')
        suggestion = session.suggest()
        assert suggestion['calibration_metrics']['known_samples'] == 6
        assert suggestion['calibration_metrics']['unknown_samples'] == 3
        chosen = suggestion['candidate']
        candidate = session.freeze(chosen['threshold'], chosen['ambiguity_margin'])
        assert candidate['validation_used_for_selection'] is False
        assert session.report(validation=True)['status'] == 'COVERAGE_INSUFFICIENT'
        assert session.report()['candidate'] == candidate
        checks.append('calibration_and_validation_separate')
        assert session.health()['templates_written'] == 0
        checks.append('no_store_api')
        session.close()
        assert session.health()['samples_in_ram'] == 0
        checks.append('close_drops_ram_references')
    finally:
        if session is not None: session.close()
        builtins.__import__, builtins.open = original_import, original_open
        sys.modules.pop(module_name, None)
    result = {'status': 'STANDARD_LIBRARY_SIMULATION_ONLY', 'checks_passed': len(checks),
              'checks': checks, 'source_sha256': actual, 'runtime_verified': False,
              'dpu_opened': False, 'database_opened': False, 'database_created': False,
              'field_threshold_validated': False, 'images_saved': 0, 'features_saved': 0,
              'samples': 'SYNTHETIC_AXIS_VECTORS_IN_RAM_ONLY'}
    print(json.dumps(result, allow_nan=False))
    return 0


if __name__ == '__main__': raise SystemExit(main())
