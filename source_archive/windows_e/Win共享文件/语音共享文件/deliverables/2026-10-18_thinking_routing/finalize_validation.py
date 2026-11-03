"""Archive intent-routing evidence without confusing cache cues with answers."""
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import sys
import zipfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / 'aura'))
from common.thinking_policy import route


def read(name):
    return json.loads((HERE / name).read_text(encoding='utf-8-sig'))


baseline = read('baseline_manifest.json')
for name, digest in baseline['preserved'].items():
    assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == digest, name
result = re.search(r'(\d+) passed, (\d+) subtests passed in ([\d.]+)s',
                   (HERE / 'tests.log').read_text(encoding='utf-8-sig'))
assert result and int(result[1]) == 106 and int(result[2]) == 26
case = read('reasoning_host.json')['cases'][0]
assert case['start']['thinking_mode'] == 'reasoning' and case['end']['thinking_mode'] == 'reasoning'
assert 'request_to_hint_event_ms' in case
assert case['end']['thinking_characters'] > 0
assert '174' in case['reply'] or '一百七十四' in case['reply'], case['reply']
summary = {'status': 'PASS_ROUTING_RULES_DEPLOYED_REAL_REASONING_CHAT_PLAYBACK_PENDING',
           'tests': {'passed': int(result[1]), 'subtests_passed': int(result[2]), 'seconds': float(result[3])},
           'routing_comparison': read('routing_after.json'), 'actual_reasoning_http': case,
           'host_health': read('host_ready.json'),
           'source_sha256': {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in baseline['before']},
           'preserved_source_sha256': baseline['preserved'],
           'user_listening_accepted': False, 'acoustic_onset_measured': False}
live_path = HERE / 'live_playback.json'
if live_path.is_file():
    live = read('live_playback.json')
    assert live['status'] == 'PASS_FRESH_CHAT_NO_WAITING_CUE_CONTINUOUS_PLAYBACK'
    assert live['board_boot_id'] == read('board_preflight.json')['camera']['board_boot_id']
    spec = importlib.util.spec_from_file_location('routing_before_snapshot', HERE / 'before/aura__common__thinking_policy.py')
    old = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(old)
    before, after = old.route(live['transcript']), route(live['transcript'])
    assert before['mode'] == 'reasoning' and after['mode'] == 'chat'
    assert live['turn']['thinking_mode'] == 'chat' and not live['turn']['thinking_feedback']
    summary['fresh_production_chat'] = live
    summary['same_recognized_text_routing'] = {'raw_text': live['transcript'], 'before': before, 'after': after}
    summary['status'] = 'PASS_ROUTING_FRESH_CHAT_PLAYBACK_AND_REAL_REASONING_LISTENING_PENDING'
    if (HERE / 'listening.json').is_file():
        hearing = read('listening.json')
        assert hearing['request_id'] == live['playback_ack']['request_id']
        summary['listening'] = hearing
        if hearing.get('accepted') is True:
            summary['user_listening_accepted'] = True
            summary['status'] = 'PASS_ROUTING_FRESH_CHAT_AND_REASONING_LISTENING_ACCEPTED'
encoded = json.dumps(summary, ensure_ascii=False, indent=2) + '\n'
(HERE / 'verification_summary.json').write_text(encoded, encoding='utf-8')
analysis = ROOT.parent / '语言模型分析'
(analysis / '思考误触发修复_实测摘要_20261018.json').write_text(encoded, encoding='utf-8')
(analysis / '思考误触发修复_20261018.md').write_text((HERE / 'README.md').read_text(encoding='utf-8'), encoding='utf-8')
with zipfile.ZipFile(HERE / 'verified_source.zip', 'w', zipfile.ZIP_DEFLATED) as archive:
    for name in [*baseline['preserved'], *baseline['before']]:
        archive.write(ROOT / name, name)
    for path in sorted(HERE.rglob('*')):
        if path.is_file() and path.suffix in {'.py', '.ps1', '.md', '.json', '.log'} and path.stat().st_size < 5_000_000:
            archive.write(path, str(path.relative_to(ROOT)).replace('\\', '/'))
with zipfile.ZipFile(HERE / 'verified_source.zip') as archive:
    assert archive.testzip() is None
print(json.dumps({'status': summary['status'], 'tests': summary['tests'],
                  'reasoning_reply': case['reply'], 'listening_accepted': summary['user_listening_accepted']}, ensure_ascii=True))
