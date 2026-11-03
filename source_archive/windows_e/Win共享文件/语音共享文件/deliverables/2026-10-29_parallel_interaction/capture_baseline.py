"""Current source/runtime identities; no chat text or biometric contents."""
import datetime,hashlib,json,sys
from pathlib import Path
H=Path(__file__).resolve().parent;P=H.parents[1];A=P/'aura'
sys.path[:0]=[str(A),str(H.parent/'2026-10-29_audio_animation_polish'),str(H.parent/'2026-10-29_service_recovery')]
from board_guard import capture
from recovery_common import windows
from common.voice_service_capabilities import SOURCE_FILES,source_fingerprint
assert not (H/'baseline.json').exists()
names=set(SOURCE_FILES)|{'tools/device_hub.py','tools/speaker_device.py','common/speaker_attribution.py',
 'common/voice_service_capabilities.py','board/runtime/audio/channel_jobs.py'}
sources={}
for name in sorted(names):
    path=A/name
    if not path.exists():continue
    raw=path.read_bytes();sources[name]=hashlib.sha256(raw).hexdigest()
    if name.endswith('.py'):
        backup=H/'source_before'/name;backup.parent.mkdir(parents=True,exist_ok=True);backup.write_bytes(raw)
v={'checked_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'voice_fingerprint':source_fingerprint(A),
   'sources':sources,'model_storage_sha256':hashlib.sha256((A/'config/model_storage.local.json').read_bytes()).hexdigest(),
   'board':capture(),'windows':windows(),'read_only':True}
(H/'baseline.json').write_text(json.dumps(v,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'status':'BASELINE_CAPTURED','voice_fingerprint':v['voice_fingerprint'],
 'board_runtime':v['board']['actual_runtime'],'board_safe':v['board']['safe'],'source_files':len(sources)}))
