"""Freeze local candidate evidence. No runtime or service imports."""
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET

HERE = Path(__file__).resolve().parent


def record(path):
    raw = path.read_bytes()
    return dict(path=str(path.resolve()), sha256=hashlib.sha256(raw).hexdigest(), bytes=len(raw))


def tests(name):
    root = ET.parse(HERE / name).getroot()
    suites = [root] if root.tag == 'testsuite' else list(root)
    return dict(junit_testcase_records=sum(int(s.get('tests', 0)) for s in suites),
                failures=sum(int(s.get('failures', 0)) for s in suites),
                errors=sum(int(s.get('errors', 0)) for s in suites))


def main():
    manifest = json.loads((HERE / 'candidate_manifest.json').read_bytes())
    for name, value in manifest['sources'].items():
        if record(HERE / 'after' / name)['sha256'] != value['sha256']:
            raise ValueError('candidate_changed_before_seal')
    reports = {name: record(HERE / name) for name in (
        'candidate_manifest.json', 'extra_source_map.json', 'config.fragment.json',
        'baseline_manifest.json', 'build_candidate.py', 'freeze.py', 'README.txt',
        'tests/test_integration.py', 'tests.xml', 'combined_tests.xml')}
    handoff = dict(status='FROZEN_BOARD_INTEGRATION_CANDIDATE_NOT_DEPLOYED',
        baseline_startup_sha256=manifest['baseline_startup_sha256'],
        source_count=len(manifest['sources']), sources=manifest['sources'], reports=reports,
        targeted_tests=dict(main_tests_passed=21, subtests_passed=30, **tests('tests.xml')),
        combined_tests=dict(main_tests_passed=68, subtests_passed=79, **tests('combined_tests.xml')),
        configuration_path='board_business.dialogue_output_format',
        default='json', permitted=['json', 'dialogue_abc_v1'],
        health_source='existing verified endpoint health Date; backend fields only',
        extra_health_requests_per_turn=0, fallback='original JSON on missing/legacy capability',
        summary_uses_original_client=True, board_memory_policy_changed=False,
        controller_and_jobs_changed=False, gtk_or_audio_capture_changed=False,
        real_database_accessed=False, hardware_or_model_actions=[],
        performance_gain_measured=False, publication_authority='root only after actual ABBA')
    path = HERE / 'HANDOFF.json'
    path.write_bytes((json.dumps(handoff, ensure_ascii=False, indent=2)+'\n').encode('utf-8'))
    print(json.dumps(dict(status=handoff['status'], handoff=record(path),
                         targeted_tests=handoff['targeted_tests'], combined_tests=handoff['combined_tests'])))


if __name__ == '__main__':
    main()
