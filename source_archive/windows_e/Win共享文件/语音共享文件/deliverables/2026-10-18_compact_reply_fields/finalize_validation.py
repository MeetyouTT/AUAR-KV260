"""Archive compact-field validation, keeping machine checks and hearing separate."""
import hashlib
import json
from pathlib import Path
import re
import zipfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def read(name):
    return json.loads((HERE / name).read_text(encoding='utf-8-sig'))


baseline = read('baseline_manifest.json')
preserved = baseline['preserved']
for name, digest in preserved.items():
    assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == digest, name
profile = read('paired_profile.json')
assert profile['all_memory_checks_passed']
log = (HERE / 'tests.log').read_text(encoding='utf-8-sig')
tests = re.search(r'(\d+) passed in ([\d.]+)s', log)
assert tests and int(tests[1]) == 75
host = read('compact_host.json')
case = host['cases'][0]
assert 'request_to_hint_event_ms' not in case
assert case['end']['thinking_mode'] == 'chat' and case['end']['clauses'] == 1
ready = read('host_ready.json')
assert ready['ready'] and not ready['busy']
status = 'PASS_COMPACT_FIELDS_DEPLOYED_REAL_HOST_LISTENING_PENDING'
summary = {'status': status, 'model': profile['model'],
           'tests': {'passed': int(tests[1]), 'seconds': float(tests[2])},
           'llm_paired_profile': profile['summary'],
           'all_memory_checks_passed': True, 'host_health': ready,
           'host_first_pcm_ms': case['request_to_first_pcm_ms'],
           'host_reply': case['reply'], 'host_tts_cache_hits': case['end']['tts_cache_hits'],
           'host_waiting_cue_events': 0, 'host_tts_clauses': 1,
           'preserved_source_sha256': preserved,
           'changed_source_sha256': {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
                                    for name in baseline['changed_before']},
           'one_second_goal_achieved': False, 'acoustic_onset_measured': False,
           'user_listening_accepted': False}
live_path = HERE / 'live_playback.json'
if live_path.is_file():
    live = read('live_playback.json')
    assert live['status'] == 'PASS_FRESH_CHAT_NO_WAITING_CUE_CONTINUOUS_PLAYBACK'
    assert live['board_boot_id'] == read('board_preflight.json')['camera']['board_boot_id']
    summary['fresh_production_playback'] = live
    summary['status'] = 'PASS_COMPACT_FIELDS_FRESH_PRODUCTION_PLAYBACK_LISTENING_PENDING'
    if (HERE / 'listening.json').is_file():
        listening = read('listening.json')
        assert listening['request_id'] == live['playback_ack']['request_id']
        summary['listening'] = listening
        summary['user_listening_accepted'] = listening.get('accepted') is True
        if summary['user_listening_accepted']:
            summary['status'] = 'PASS_COMPACT_FIELDS_FRESH_PLAYBACK_AND_LISTENING'
encoded = json.dumps(summary, ensure_ascii=False, indent=2) + '\n'
(HERE / 'verification_summary.json').write_text(encoded, encoding='utf-8')
(ROOT.parent / '语言模型分析/27B内部短字段优化_实测摘要_20261018.json').write_text(encoded, encoding='utf-8')
with zipfile.ZipFile(HERE / 'verified_source.zip', 'w', zipfile.ZIP_DEFLATED) as archive:
    for name in [*preserved, *baseline['changed_before']]:
        archive.write(ROOT / name, name)
    for path in sorted(HERE.rglob('*')):
        if path.is_file() and path.suffix in {'.py', '.ps1', '.md', '.json', '.log'} and path.stat().st_size < 5_000_000:
            archive.write(path, str(path.relative_to(ROOT)).replace('\\', '/'))
with zipfile.ZipFile(HERE / 'verified_source.zip') as archive:
    assert archive.testzip() is None
print(json.dumps({'status': summary['status'], 'tests': summary['tests'],
                  'host_first_pcm_ms': summary['host_first_pcm_ms'],
                  'user_listening_accepted': summary['user_listening_accepted']}))
