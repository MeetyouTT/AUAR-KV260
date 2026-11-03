import base64
import hashlib
import json
from pathlib import Path

runtime=Path('/home/root/aura-avatar-gtk-stage/runtime-1a8677ce-20261009')
paths=['aura/tools/board_avatar_gtk.py','aura/tools/board_recording.py','aura/tools/realtime_controller.py',
       'aura/tools/selected_voice_service.py','aura/board/runtime/audio/transcription.py',
       'aura/board/runtime/audio/conversation.py','aura/common/voice_wire.py',
       'avatar_conversation_settings.json']
launcher=Path('/home/root/aura-ui-startup-20261009/releases/d2e45eb7fee4fa08/config.json')
report={'runtime':str(runtime),'files':{},'launcher_config_path':str(launcher),'launcher_config':json.loads(launcher.read_text())}
for name in paths:
    path=runtime/name
    raw=path.read_bytes() if path.exists() else None
    report['files'][name]=None if raw is None else {'sha256':hashlib.sha256(raw).hexdigest(),'base64':base64.b64encode(raw).decode()}
print(json.dumps(report))
