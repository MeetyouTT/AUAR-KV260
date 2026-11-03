"""Archive this startup's evidence without promoting earlier playback to a pass."""
import hashlib
import json
from pathlib import Path
import zipfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
ANALYSIS = ROOT.parent / '语言模型分析'


def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


summary = read(HERE / 'verification_summary.json')
resume = read(HERE / 'resume_status.json')
assert resume['status'] == 'PASS_REAL_HOST_CHAT_NO_WAITING_CUE'
assert resume['waiting_hint_events'] == 0 and resume['tts_clauses'] == 1
assert resume['host_health']['ready'] and not resume['host_health']['busy']
for name, digest in summary['source_sha256'].items():
    assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == digest, name
summary['resume_validation'] = resume
summary['status'] = 'CHAT_CUE_FIX_DEPLOYED_REAL_HOST_PASS_LISTENING_PENDING'
summary['waiting_prompt_fix'].update(deployed=True, requires=None,
                                    runtime_listening_verified=False)
live_path = HERE / 'resume_live_playback.json'
if live_path.is_file():
    live = read(live_path)
    assert live['board_boot_id'] == resume['board_boot_id']
    assert live['status'] == 'PASS_FRESH_CHAT_NO_WAITING_CUE_CONTINUOUS_PLAYBACK'
    summary['resume_playback'] = live
    summary['status'] = 'CHAT_CUE_FIX_DEPLOYED_FRESH_PLAYBACK_PASS_LISTENING_PENDING'
listening_path = HERE / 'resume_listening.json'
if listening_path.is_file():
    summary['resume_listening'] = read(listening_path)
    if live_path.is_file() and summary['resume_listening'].get('accepted') is True:
        summary['waiting_prompt_fix']['runtime_listening_verified'] = True
        summary['status'] = 'CHAT_CUE_FIX_DEPLOYED_FRESH_PLAYBACK_AND_LISTENING_ACCEPTED'
encoded = json.dumps(summary, ensure_ascii=False, indent=2) + '\n'
(HERE / 'verification_summary.json').write_text(encoded, encoding='utf-8')
(ANALYSIS / '27B首段延迟优化_实测摘要_20261018.json').write_text(encoded, encoding='utf-8')
with zipfile.ZipFile(HERE / 'optimized_source.zip', 'w', zipfile.ZIP_DEFLATED) as archive:
    for name in summary['source_sha256']:
        archive.write(ROOT / name, name)
    for path in sorted(HERE.rglob('*')):
        if path.is_file() and path.suffix in {'.py', '.ps1', '.md', '.json', '.log'} and path.stat().st_size < 5_000_000:
            archive.write(path, str(path.relative_to(ROOT)).replace('\\', '/'))
with zipfile.ZipFile(HERE / 'optimized_source.zip') as archive:
    assert archive.testzip() is None
print(json.dumps({'status': summary['status'], 'tests': summary['tests'],
                  'deployed': True, 'listening_accepted': summary['waiting_prompt_fix']['runtime_listening_verified']}))
