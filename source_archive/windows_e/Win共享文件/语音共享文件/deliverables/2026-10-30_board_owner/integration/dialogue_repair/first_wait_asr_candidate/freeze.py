"""Seal only this agent's explicit files; root_runner.py is intentionally excluded."""
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
NAMES = ('after/board/runtime/audio/board_asr.py', 'before/board/runtime/audio/board_asr.py',
         'candidate_manifest.json', 'extra_source_map.json', 'probe_asr_abba.py',
         'build_candidate.py', 'tests/test_asr_four.py', 'tests.xml', 'README.txt', 'freeze.py')


def main():
    files = {}
    for name in NAMES:
        path = HERE/name
        raw = path.read_bytes()
        files[name] = dict(path=str(path.resolve()), sha256=hashlib.sha256(raw).hexdigest(), bytes=len(raw))
    manifest = json.loads((HERE/'candidate_manifest.json').read_bytes())
    if files['after/board/runtime/audio/board_asr.py']['sha256'] != manifest['board/runtime/audio/board_asr.py']['sha256']:
        raise ValueError('candidate_changed_before_seal')
    value = dict(status='SOURCE_AND_ROOT_ONLY_PUBLIC_PROBE_FROZEN_NOT_DEPLOYED', files=files,
        baseline_startup_sha256='39b102a4a505db491cf06b90e3a5232bfb656c79cb0a3c221551d76d414a9a0a',
        production_source_files=1, production_default_threads=2, production_configuration_changed=False,
        probe_sequence=[3,4,4,3], extra_probe_models_at_once=1, production_asr_also_resident=True,
        targeted_tests=dict(main_tests_passed=15, subtests_passed=9, failed=0),
        background_changes_preserve_measurements=True, background_changes_allow_gain_claim=False,
        inference_performed_by_agent=False, hardware_operations_by_agent=[],
        production_db_accessed=False, actual_gain_measured=False,
        source_only=True, root_runner_owned_by_parent_not_included=True)
    path = HERE/'HANDOFF.json'
    path.write_bytes((json.dumps(value, ensure_ascii=False, indent=2)+'\n').encode('utf-8'))
    print(json.dumps(dict(status=value['status'], handoff_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
        probe_sha256=files['probe_asr_abba.py']['sha256'], candidate_sha256=files['after/board/runtime/audio/board_asr.py']['sha256'])))


if __name__ == '__main__': main()
