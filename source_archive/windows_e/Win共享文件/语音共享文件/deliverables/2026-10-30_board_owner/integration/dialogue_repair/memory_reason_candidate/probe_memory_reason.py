"""One localhost metadata read via the existing SSH owner; no database/model calls.

Only main() performs IO. The extractor is pure and can be tested offline.
"""
import argparse
import inspect
import json
from pathlib import Path
import re
import sys


def extract_memory_reason(state):
    import math
    counts = dict(missing_fields=0, unknown_enum_values=0,
                  unknown_rejection_reasons=0, invalid_numeric_values=0)

    def obj(value):
        return value if isinstance(value, dict) else {}

    def number(value):
        if value is None:
            counts['missing_fields'] += 1
            return None
        if type(value) in (int, float) and 0 <= value < 2 ** 53 and math.isfinite(value):
            return value
        counts['invalid_numeric_values'] += 1
        return None

    def boolean(value):
        if type(value) is bool:
            return value
        counts['missing_fields'] += 1
        return None

    def enum(value, allowed):
        if value is None:
            counts['missing_fields'] += 1
            return 'unavailable'
        if type(value) is str and value in allowed:
            return value
        counts['unknown_enum_values'] += 1
        return 'unknown'

    worker_codes = {'', 'none', 'model_failed', 'candidate_rejected', 'cancelled',
                    'deadline_exceeded', 'database_busy', 'compaction_failed', 'clock_unverified'}
    reply_codes = {'none', 'cancelled', 'preempted', 'superseded', 'foreground_busy',
                   'deadline_exceeded', 'backend_failed', 'backend_invalid_result', 'gpu_busy',
                   'startup_busy', 'queue_full', 'owner_capacity', 'duplicate_request',
                   'stale_generation', 'shutdown', 'tts_owner_conflict', 'tts_ownership_unavailable',
                   'context_limit', 'candidate_rejected', 'operation_failed', 'other'}
    stages = {'idle', 'prepare', 'admission', 'model_request', 'wire_response', 'semantic_json',
              'semantic_shape', 'semantic_bounds', 'structured_camera_counts', 'fragmentation',
              'fragment_validation', 'reduction', 'reduction_validation', 'full_source_validation', 'complete'}
    classes = {'none', 'other', 'InterruptedError', 'TimeoutError', 'RuntimeError', 'ValueError',
               'CandidateRejected', 'ContextLimitError', 'ModelRequestError', 'WireError',
               'MemoryBusy', 'ClockUnavailable', 'OSError', 'ConnectionError', 'ConnectionRefusedError',
               'ConnectionResetError', 'JSONDecodeError', 'TypeError', 'KeyError', 'AttributeError',
               'AssertionError', 'NameError', 'NotImplementedError', 'OperationalError', 'DatabaseError'}
    rejection_codes = ('protected_name_missing', 'protected_number_missing_or_changed', 'negation_missing',
                       'planned_status_missing', 'completed_status_missing', 'cancelled_status_missing',
                       'observation_evidence_missing')
    business = obj(obj(state).get('board_business'))
    memory = obj(business.get('memory'))
    retry = obj(memory.get('retry_backoff'))
    summary = obj(memory.get('summary_diagnostics'))
    reasons = summary.get('rejection_reasons', [])
    if not isinstance(reasons, (list, tuple)):
        counts['unknown_rejection_reasons'] += 1
        reasons = []
    accepted = []
    # A bounded vocabulary; arbitrary strings and unexpected containers never leave RAM.
    for reason in reasons[:64]:
        if type(reason) is str and reason in rejection_codes:
            if reason not in accepted:
                accepted.append(reason)
        else:
            counts['unknown_rejection_reasons'] += 1
    if len(reasons) > 64:
        counts['unknown_rejection_reasons'] += len(reasons) - 64
    clock = obj(business.get('clock'))
    refresh = obj(business.get('clock_refresh'))
    observed = {
        'schema': 'aura.memory-reason-metadata.v1',
        'phase': enum(obj(state).get('phase'), {'IDLE', 'VOICE_PREPARING', 'VOICE_STARTING', 'SPEAKING', 'ACTION', 'ERROR'}),
        'worker': dict(running=boolean(memory.get('running')), completed=number(memory.get('completed')),
                       discarded=number(memory.get('discarded')),
                       error_present=bool(memory.get('error')),
                       error_is_presentation_redaction=memory.get('error') == 'operation_failed'),
        'retry': dict(last_failure_code=enum(retry.get('last_failure_code'), worker_codes),
                      failure_streak=number(retry.get('failure_streak')),
                      retry_in_seconds=number(retry.get('retry_in_seconds')),
                      last_delay_seconds=number(retry.get('last_delay_seconds')),
                      maximum_seconds=number(retry.get('maximum_seconds'))),
        'summary': dict(state=enum(summary.get('state'), {'idle', 'complete', 'failed', 'deferred'}),
                        stage=enum(summary.get('stage'), stages), code=enum(summary.get('code'), reply_codes),
                        error_class=enum(summary.get('error_class'), classes),
                        method=enum(summary.get('method', 'none'), {'none', 'structured_camera_counts'}),
                        rejection_reasons=accepted),
        'clock': {key: boolean(clock.get(key)) for key in ('safe_for_compaction', 'anchored', 'persistent', 'same_boot')},
        'clock_refresh': dict(error_present=bool(refresh.get('error')),
                              retry_in_seconds=number(refresh.get('retry_in_seconds'))),
    }
    for key in ('verified_age_seconds', 'uncertainty_seconds'):
        observed['clock'][key] = number(clock.get(key))
    observed['unknown_counts'] = counts
    return observed


def remote_source(expected_startup, expected_boot):
    # Expected values are validated locally; output contains matches, never IDs/hashes.
    source = 'import hashlib,http.client,json,pathlib,time\n' + inspect.getsource(extract_memory_reason)
    source += '\nEXPECTED_STARTUP=' + repr(expected_startup) + '\nEXPECTED_BOOT=' + repr(expected_boot) + '\n'
    source += '''
def read_once():
    boot = pathlib.Path('/proc/sys/kernel/random/boot_id').read_text().strip()
    config = pathlib.Path('/home/root/aura-board-business-20261030/production-5259eab11e42af13/startup/config.json')
    if boot != EXPECTED_BOOT:
        return dict(status='rejected', code='boot_mismatch')
    if hashlib.sha256(config.read_bytes()).hexdigest() != EXPECTED_STARTUP:
        return dict(status='rejected', code='configuration_pin_mismatch')
    c = http.client.HTTPConnection('127.0.0.1', 8783, timeout=5)
    try:
        c.request('GET', '/api/state')
        r = c.getresponse()
        data = r.read(1048577)
        if r.status != 200 or len(data) > 1048576:
            return dict(status='rejected', code='http_response_rejected')
        state = json.loads(data)
    finally:
        c.close()
    if not isinstance(state, dict):
        return dict(status='rejected', code='state_shape_rejected')
    business = state.get('board_business')
    if not isinstance(business, dict) or business.get('data_origin') != 'board' or business.get('started') is not True:
        return dict(status='rejected', code='business_not_ready')
    writer = business.get('writer')
    if not isinstance(writer, dict) or writer.get('boot_id') != EXPECTED_BOOT or writer.get('held') is not True:
        return dict(status='rejected', code='writer_boot_mismatch')
    # Check again after HTTP: do not adopt a result spanning a configuration update.
    if hashlib.sha256(config.read_bytes()).hexdigest() != EXPECTED_STARTUP:
        return dict(status='rejected', code='configuration_pin_mismatch')
    result = extract_memory_reason(state)
    result.update(status='metadata_read', observed_mono=time.monotonic(),
                  boot_match=True, configuration_file_pin_match=True,
                  no_database_or_model_access=True, snapshot_atomicity_verified=False)
    return result
try:
    result = read_once()
except Exception:
    result = dict(status='rejected', code='metadata_read_failed')
print(json.dumps(result, separators=(',', ':')))
'''
    return source


def main():
    p = argparse.ArgumentParser()
    p.add_argument('label')
    p.add_argument('--expected-startup-sha', required=True)
    p.add_argument('--expected-boot-id', required=True)
    args = p.parse_args()
    if not re.fullmatch(r'[A-Za-z0-9_]{1,64}', args.label):
        raise SystemExit('invalid_label')
    if not re.fullmatch(r'[a-f0-9]{64}', args.expected_startup_sha):
        raise SystemExit('invalid_expected_pin')
    if not re.fullmatch(r'[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}', args.expected_boot_id):
        raise SystemExit('invalid_expected_boot')
    target = Path(__file__).resolve().parent / ('actual_' + args.label + '.json')
    if target.exists():
        raise SystemExit('metadata_output_exists')
    try:
        project = Path(__file__).resolve().parents[5]
        sys.path.insert(0, str(project / 'deliverables/2026-10-18_board_dialogue'))
        from board_ssh import ssh
        raw = ssh('python3 -B -', remote_source(args.expected_startup_sha, args.expected_boot_id), timeout=15)
        value = json.loads(raw)
        if not isinstance(value, dict) or value.get('status') not in ('metadata_read', 'rejected'):
            raise ValueError()
    except Exception:
        value = dict(status='rejected', code='probe_transport_failed')
    with target.open('x', encoding='utf-8') as f:
        f.write(json.dumps(value, ensure_ascii=True, indent=2) + '\n')
    print(json.dumps(value, ensure_ascii=True))
    return 0 if value['status'] == 'metadata_read' else 2


if __name__ == '__main__':
    raise SystemExit(main())
