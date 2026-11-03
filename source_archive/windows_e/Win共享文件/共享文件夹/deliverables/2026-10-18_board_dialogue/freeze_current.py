"""Snapshot this iteration's sources and evidence without models or private keys."""
import hashlib
import argparse
import json
from pathlib import Path
import zipfile

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
names=['aura/common/voice_wire.py','aura/tools/board_model_host.py','aura/tools/asr_server.py',
       'aura/board/runtime/audio/conversation.py','aura/board/runtime/audio/transcription.py',
       'aura/tools/selected_voice_service.py','aura/tools/realtime_controller.py',
       'aura/tools/board_recording.py','aura/tools/board_avatar_gtk.py',
       'aura/tests/framework/test_conversation.py','aura/tests/framework/test_asr_disconnect.py',
       'README.md','.cline-handover.md','aura/.cline-handover.md']
parser=argparse.ArgumentParser();parser.add_argument('--live-verified',action='store_true');args=parser.parse_args()
archive=HERE/('board_dialogue_live_verified_source.zip' if args.live_verified else 'board_dialogue_source.zip')
sources=[ROOT/name for name in names]
sources.extend(p for p in HERE.rglob('*') if p.is_file() and p.suffix in {'.py','.ps1','.sh','.pub','.md','.json','.log','.png','.wav'}
               and p.name not in {'source_snapshot.json','live_source_snapshot.json','deployment_payload.json'})
rows=[]
with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
    for path in sorted(set(sources)):
        raw=path.read_bytes();name=path.relative_to(ROOT).as_posix();z.writestr(name,raw)
        rows.append({'path':name,'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()})
with zipfile.ZipFile(archive) as z:assert z.testzip() is None
live=HERE/'live_turn_verification.json'
report={'status':'PASS_SOURCE_SNAPSHOT','files':rows,'archive_bytes':archive.stat().st_size,
        'archive_sha256':hashlib.sha256(archive.read_bytes()).hexdigest(),
        'scope':'Snapshot entry bytes, not mutable service logs after archive creation',
        'live_verification':json.loads(live.read_text(encoding='utf-8'))['status'] if live.exists() else 'NOT_COMPLETE',
        'private_keys_included':False,'model_weights_included':False}
(HERE/('live_source_snapshot.json' if args.live_verified else 'source_snapshot.json')).write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print('SNAPSHOT_PASS',len(rows),'files',report['archive_bytes'],'bytes')
