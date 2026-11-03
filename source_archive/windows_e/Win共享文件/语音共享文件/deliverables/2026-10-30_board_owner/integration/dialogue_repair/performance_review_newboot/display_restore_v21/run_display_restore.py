"""Root-only X preflight or restoration, with default local validation."""
import argparse
import ast
import importlib.util
import json
from pathlib import Path
import sys
import time

import display_restore as worker


HERE = Path(__file__).resolve().parent
REPAIR = HERE.parent.parent
PUBLISHER = REPAIR / 'release_v21_asr2_display_candidate'
COMMON_SHA = 'def9f922bc4dd2abd1e6608923d0408b0ec9cdb8ccfa89d2534742892242e11d'
SEAL_SHA = 'f2b9afbe0290688e549565c446b1790c53586255029338b2c58a8fadd0356651'
EVIDENCE = PUBLISHER / 'asr2_display_evidence'
SPEC_SHA = '8dcd958d07de22f996d5f406ab399cdf51e252b1cbd209fac9fdbc6cae8d87a7'
READY_SHA = '2825ff9e0828d6c0a156f0bc0e819d2b850d57d98665ee614801ca94d568cbd0'
MAPPING_SHA = 'bff1b76381914cfa070c617e21ce091e8b97a8b7062f408c842cbcf03bc5dee2'


def load_pinned(path, pin, name):
    raw = path.read_bytes()
    worker.need(worker.sha(raw) == pin, 'FROZEN_PUBLISHER_CHANGED')
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def local_inputs(spec_path, spec_sha, ready_path, ready_sha):
    worker.need(spec_sha == SPEC_SHA and ready_sha == READY_SHA, 'ACTUAL_SEALED_V21_INPUTS_REQUIRED')
    common = load_pinned(PUBLISHER / 'stability_common.py', COMMON_SHA, '_v21_display_common')
    # The sealed read-only guard imports this exact module name locally.
    sys.modules['stability_common'] = common
    seal = load_pinned(PUBLISHER / 'seal_stability.py', SEAL_SHA, '_v21_display_seal')
    spec = common.validate_spec(json.loads(common.pinned(spec_path, spec_sha)))
    ready = json.loads(common.pinned(ready_path, ready_sha))
    worker.need(spec['startup_sha256'] == worker.STARTUP_SHA and spec['expected_final_listening_enabled'] is False,
                'EXACT_PAUSED_V21_REQUIRED')
    worker.need(ready.get('status') == 'PRODUCTION_BOARD_BUSINESS_READY' and ready.get('guard_removed') is True
                and ready.get('root') == spec['target'] and ready.get('listening_enabled') is False
                and ready.get('listening_state') == 'PAUSED' and ready.get('physical_microphone_opened') is False
                and all(type(ready.get(k)) is int and ready[k] > 0 for k in ('main_pid', 'gtk_pid')),
                'ACTUAL_PAUSED_READY_REQUIRED')
    products = {key: value['sha256'] for key, value in common.approved_sources().items()}
    mapping = json.loads(common.pinned(EVIDENCE / 'source_mapping.json', MAPPING_SHA))
    seal.validate_mapping(mapping, spec, ready, products)
    owners = {key: mapping[key] for key in ('boot_id', 'startup_sha256', 'source_manifest_sha256',
              'configuration_sha256', 'supervisor', 'gtk', 'camera')}
    return common, dict(spec=spec, ready=ready, products=products, guard_source=seal.REMOTE,
                        baseline_owners=owners)


def build_remote():
    source = (HERE / 'display_restore.py').read_bytes().decode('utf-8')
    source += '''
def expired(signum, frame):
    raise Refused('BOUNDED_DISPLAY_OPERATION_TIMEOUT')
import signal
signal.signal(signal.SIGALRM, expired)
signal.alarm(90)
try:
    result = execute(ARGUMENTS)
finally:
    signal.alarm(0)
print(json.dumps(result, sort_keys=True))
'''
    ast.parse(source, feature_version=(3, 9))
    return source


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('preflight', 'restore-observe'))
    parser.add_argument('--spec', default=EVIDENCE / 'spec.json', type=Path)
    parser.add_argument('--spec-sha256', default=SPEC_SHA)
    parser.add_argument('--ready', default=EVIDENCE / 'ready.json', type=Path)
    parser.add_argument('--ready-sha256', default=READY_SHA)
    parser.add_argument('--preflight', type=Path)
    parser.add_argument('--preflight-sha256')
    parser.add_argument('--execute-root-only', action='store_true')
    args = parser.parse_args()
    common, arguments = local_inputs(args.spec, args.spec_sha256, args.ready, args.ready_sha256)
    arguments.update(action=args.action, token=time.time_ns(), preflight=None)
    if args.action == 'restore-observe':
        worker.need(args.preflight is not None and args.preflight_sha256, 'EXACT_PREFLIGHT_RECEIPT_REQUIRED')
        arguments['preflight'] = json.loads(common.pinned(args.preflight, args.preflight_sha256))
    remote = build_remote()
    if not args.execute_root_only:
        print(json.dumps(dict(status='DRY_DISPLAY_OPERATION_VALIDATED', action=args.action,
            remote_sha256=worker.sha(remote.encode()), startup_sha256=worker.STARTUP_SHA,
            device_access=False, microphone_control_sent=False)))
        return
    result = common.execute_remote(remote, dict(ARGUMENTS=arguments), timeout=120)
    output = HERE / ('actual_' + args.action + '_' + str(arguments['token']) + '.json')
    pin = common.write_new_json(output, result)
    print(json.dumps(dict(output=str(output), sha256=pin, result=result), ensure_ascii=True))


if __name__ == '__main__':
    main()
