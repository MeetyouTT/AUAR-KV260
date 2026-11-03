"""Package actual speech-interpretation checks without claiming ASR retraining."""
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
for name, digest in baseline['preserved'].items():
    assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == digest, name
review = read('interpretation_review.json')
assert review['all_passed']
match = re.search(r'(\d+) passed in ([\d.]+)s', (HERE / 'tests.log').read_text(encoding='utf-8-sig'))
assert match and int(match[1]) == 104
case = read('speech_tolerance_host.json')['cases'][0]
edits = case['transcript_event']['input_adjustments']
assert edits == case['end']['timing']['input_adjustments']
assert any(e['from'] == '西兰' and e['to'] == '汐蓝' for e in edits)
assert '西兰' not in case['reply'] and case['end']['clauses'] == 1
assert 'request_to_hint_event_ms' not in case
ready = read('host_ready.json')
assert ready['ready']
names = [*baseline['before'], 'aura/common/spoken_input.py', 'aura/tests/framework/test_spoken_input.py']
summary = {'status': 'PASS_SPOKEN_NAME_TOLERANCE_DEPLOYED_HOST_LISTENING_PENDING',
           'scope': 'known character-vocative homophones; preserve raw ASR and other words',
           'asr_model_changed': False, 'general_pronunciation_accuracy_verified': False,
           'host_health': ready, 'tests': {'passed': int(match[1]), 'seconds': float(match[2])},
           'real_27b_text_checks': review, 'actual_recording_http': case,
           'source_sha256': {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in names},
           'preserved_source_sha256': baseline['preserved'],
           'user_listening_accepted': False, 'acoustic_onset_measured': False}
live_path = HERE / 'live_playback.json'
if live_path.is_file():
    live = read('live_playback.json')
    assert live['status'] == 'PASS_FRESH_CHAT_NO_WAITING_CUE_CONTINUOUS_PLAYBACK'
    assert live['board_boot_id'] == read('board_preflight.json')['camera']['board_boot_id']
    assert '西兰' not in live['turn']['text']
    summary['fresh_production_playback'] = live
    summary['status'] = 'PASS_SPOKEN_NAME_TOLERANCE_FRESH_PLAYBACK_LISTENING_PENDING'
    if (HERE / 'listening.json').is_file():
        hearing = read('listening.json')
        assert hearing['request_id'] == live['playback_ack']['request_id']
        summary['listening'] = hearing
        if hearing.get('accepted') is True:
            summary['user_listening_accepted'] = True
            summary['status'] = 'PASS_SPOKEN_NAME_TOLERANCE_FRESH_PLAYBACK_AND_LISTENING'
encoded = json.dumps(summary, ensure_ascii=False, indent=2) + '\n'
(HERE / 'verification_summary.json').write_text(encoded, encoding='utf-8')
analysis = ROOT.parent / '语言模型分析'
(analysis / '汐蓝称呼误听容错_实测摘要_20261018.json').write_text(encoded, encoding='utf-8')
(analysis / '汐蓝称呼误听容错_20261018.md').write_text((HERE / 'README.md').read_text(encoding='utf-8'), encoding='utf-8')
with zipfile.ZipFile(HERE / 'verified_source.zip', 'w', zipfile.ZIP_DEFLATED) as archive:
    for name in [*baseline['preserved'], *names]:
        archive.write(ROOT / name, name)
    for path in sorted(HERE.rglob('*')):
        if path.is_file() and path.suffix in {'.py', '.ps1', '.md', '.json', '.log'} and path.stat().st_size < 5_000_000:
            archive.write(path, str(path.relative_to(ROOT)).replace('\\', '/'))
with zipfile.ZipFile(HERE / 'verified_source.zip') as archive:
    assert archive.testzip() is None
print(json.dumps({'status': summary['status'], 'tests': summary['tests'],
                  'host_first_pcm_ms': case['request_to_first_pcm_ms'],
                  'user_listening_accepted': summary['user_listening_accepted']}))
