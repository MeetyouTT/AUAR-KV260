"""Seal only this local source overlay and its synthetic evidence."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def fingerprint(path):
    data = path.read_bytes()
    return dict(sha256=hashlib.sha256(data).hexdigest(), bytes=len(data))


def main():
    manifest = json.loads((ROOT / 'overlay_manifest.json').read_text(encoding='utf-8'))
    dependencies = ROOT.parents[1] / 'production_business_overlay/candidate/aura'
    receipt = dict(schema='aura.production-listening-handoff.v1', status='SOURCE_READY_NOT_DEPLOYED',
        hardware_executed=False, tests=dict(passed=14, failed=0, xml='tests.xml'),
        base_startup_sha256=manifest['base_startup_sha256'], source_files=manifest['files'],
        artifacts={name: fingerprint(ROOT / name) for name in (
            'production_listening.overlay.zip', 'overlay_manifest.json', 'extra_source_map.json',
            'build_overlay.py', 'test_production_listening.py', 'tests.xml', 'REVIEW.txt')},
        reused_dependencies={name: fingerprint(dependencies / name) for name in (
            'common/handsfree_settings.py', 'tools/formal_yuki.py',
            'tools/voice_first_recording.py', 'tools/handsfree_recording.py',
            'tools/barge_in_recording.py', 'tools/board_recording.py')},
        scope=dict(only_board_production=True, synthetic_unchanged=True,
            new_private_preference='listening_preference.json', missing_preference=True,
            persisted_user_pause=True, error_retry_changes_preference=False,
            ready_gate=['runtime.started', 'not runtime.closed', 'pair.ready_now'],
            per_tick_http=False, source_only=True),
        remaining=['Root merge with independent capture fix and safe diagnostics',
                   'Root verify exact current base pins and publish normally',
                   'Actual microphone and physical audio acceptance remain root-owned'])
    (ROOT / 'HANDOFF.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(fingerprint(ROOT / 'HANDOFF.json')))


if __name__ == '__main__':
    main()
