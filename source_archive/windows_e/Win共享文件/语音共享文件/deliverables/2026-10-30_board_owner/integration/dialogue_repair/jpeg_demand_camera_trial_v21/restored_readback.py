"""Explicitly bind the unchanged same-boot proof to this completed A/B/A.

Root supplies a separately reviewed authority SHA after the final original
camera owner is proven. Default invocation only produces a read-only report.
"""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import sys


HERE = Path(__file__).resolve().parent
HELPER_SHA = 'e42df5b355b627ac4a6df21086e8cf07a43b722ffc6b5c5bdd5b93f96b3b8124'
MANIFEST_SHA = '6a7c6a56a5ceda2259ddf0ee7e00fbc932d1a34d56a396202e2f4cd045fce6e1'
STAGE = '/home/root/aura-board-owner-candidate-20261030/jpeg-trial-' + MANIFEST_SHA[:16]
FIXED = {
    'executor_path': STAGE + '/serial_trial.py',
    'executor_sha256': '1e8aeee2a94b4fce674f2468ce48c77fbb88ef99bd9cb1ab66dd3bf20a0327f6',
    'journal_path': STAGE + '/journal/state.json',
    'baseline_path': '/home/root/aura-board-owner-candidate-20261030/private-pin-bebd3e7d-1335-20261031/face_gallery_readback.local.json',
    'baseline_sha256': 'c7300d1cf8b2f6c9dae7bd953ada0c55997d3a8d623703df35ff43e0f0d33df4',
    'manifest_sha256': MANIFEST_SHA,
    'boot': 'bebd3e7d-e984-4517-8cbb-211df7f1c6dc',
    'baseline_pid': 1335,
    'baseline_pin_count': 21,
}
DYNAMIC = {'candidate_pid', 'restored_pid', 'checkpoint_sha256', 'journal_sha256'}


def load_helper():
    path = HERE / 'rebuild_same_boot_readback.py'
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != HELPER_SHA:
        raise ValueError('Original same-boot helper changed')
    spec = importlib.util.spec_from_file_location('jpeg_same_boot_proof', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def validate_authority(value, helper):
    if set(value) != set(FIXED) | DYNAMIC or any(value.get(k) != v for k, v in FIXED.items()):
        raise ValueError('Exact current A/B/A authority required')
    if (not helper.sha(value['checkpoint_sha256']) or not helper.sha(value['journal_sha256'])
            or any(type(value[k]) is not int or value[k] <= 1 for k in ('candidate_pid', 'restored_pid'))
            or len({value['baseline_pid'], value['candidate_pid'], value['restored_pid']}) != 3):
        raise ValueError('Explicit distinct owners and completed journal/checkpoint SHAs required')
    return dict(value)


def prove(helper, authority, *, executor=None, system=None, reader=None):
    """Every helper call receives the same explicit authority object."""
    helper.AUTHORITY = authority
    reader = reader or helper.private_read
    if executor is None:
        executor = helper.load_executor(authority['executor_path'], authority['executor_sha256'],
                                        reader=reader, authority=authority)
    if system is None:
        system = helper.readonly_system(executor)
    return helper.build(executor, system,
                        journal_path=authority['journal_path'],
                        expected_journal_sha256=authority['journal_sha256'],
                        baseline_path=authority['baseline_path'],
                        expected_baseline_sha256=authority['baseline_sha256'],
                        executor_path=authority['executor_path'],
                        expected_executor_sha256=authority['executor_sha256'],
                        reader=reader, authority=authority)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--authority', required=True, type=Path)
    parser.add_argument('--authority-sha256', required=True)
    parser.add_argument('--write', action='store_true')
    parser.add_argument('--private-root')
    parser.add_argument('--output')
    parser.add_argument('--proof-output')
    parser.add_argument('--expected-observation-sha256')
    args = parser.parse_args()
    helper = load_helper()
    try:
        raw = helper.private_read(str(args.authority))
        helper.need(helper.sha(args.authority_sha256) and helper.digest(raw) == args.authority_sha256,
                    'reviewed_authority_sha_required')
        authority = validate_authority(helper.parse(raw), helper)
        candidate, report = prove(helper, authority)
        if args.write:
            helper.need(args.private_root and args.output and args.proof_output
                        and args.expected_observation_sha256, 'exclusive_output_paths_and_reviewed_token_required')
            again, proof = prove(helper, authority)
            helper.need(candidate == again and report['observation_sha256'] == proof['observation_sha256'],
                        'owner_or_proof_changed_before_write')
            helper.need(helper.digest(helper.private_read(str(args.authority))) == args.authority_sha256,
                        'reviewed_authority_changed_before_write')
            report = helper.write_candidate(candidate, proof, private_root=args.private_root,
                                            output=args.output, proof_output=args.proof_output,
                                            expected_observation=args.expected_observation_sha256)
        print(json.dumps(report, sort_keys=True))
        return 0
    except Exception as exc:
        print(json.dumps({'ready': False, 'written': False, 'status': type(exc).__name__,
                          'database_opened': False, 'service_action_sent': False,
                          'checkpoint_or_marker_modified': False}))
        return 2


if __name__ == '__main__':
    sys.exit(main())
