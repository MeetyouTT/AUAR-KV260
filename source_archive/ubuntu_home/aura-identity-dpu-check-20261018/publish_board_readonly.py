"""Publish only filtered board state and reviewed probe; keep raw UART local."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil

job = Path(__file__).parent
out = Path('/home/ghmd/Win共享文件/协作任务/2026-10-18_双机联调/evidence/ubuntu/identity-dpu-check-20261018/board-readonly')
status = json.loads((job/'board-readonly/status.json').read_text())
body = (job/'board-readonly/result.json').read_bytes()
assert status['complete'] and status['console_echo_restored']
assert hashlib.sha256(body).hexdigest() == status['output_sha256']
result = json.loads(body)
assert not result['recording_or_deployment_requested']
assert result['camera']['identity_recognition'] is False
out.mkdir(parents=True, exist_ok=True)
entries = []
for source, relative in [('board_readonly.py', 'board_readonly.py'), ('run_board_readonly.py', 'run_board_readonly.py'), ('board-readonly/result.json', 'result.json'), ('board-readonly/status.json', 'status.json')]:
    src = job/source
    dst = out/relative
    if dst.exists():
        assert dst.read_bytes() == src.read_bytes()
    else:
        shutil.copyfile(src, dst)
    assert dst.read_bytes() == src.read_bytes()
    entries.append({'path': relative, 'sha256': hashlib.sha256(dst.read_bytes()).hexdigest(), 'bytes': dst.stat().st_size})
summary = {'checked_utc': datetime.now(timezone.utc).isoformat(), 'scope': 'guarded_runtime_health_read_only_not_identity_board_acceptance', 'files': entries, 'uart_raw_published': False, 'transcripts_images_or_identity_features_published': False}
(out/'verification.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2)+'\n')
print(json.dumps({'files_hash_verified': len(entries), 'board_runtime_readonly': 'PASS', 'identity_recognition': False}))
