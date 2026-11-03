"""Verify current documentation links and parse changed Python without imports."""
import hashlib
import json
from pathlib import Path
import re
from urllib.parse import unquote,urlsplit

WORK=Path(__file__).resolve().parent
AURA=Path('/home/ghmd/Win共享文件/共享文件夹/aura')
docs=[WORK/'REPORT.md',AURA/'docs/BOARD_ASR.md',AURA/'docs/BOARD_AUDIO_CAPTURE.md',
      AURA/'docs/FRAMEWORK_STATUS.md',Path('/home/ghmd/AMD_Smart/logs/daily/2026-10-17-RECORDING-ASR.md')]
links=[]
for path in docs:
    for target in re.findall(r'\[[^\]]*\]\(([^)]+)\)',path.read_text()):
        url=urlsplit(target)
        if url.scheme or not url.path:continue
        resolved=Path(unquote(url.path))
        if not resolved.is_absolute():resolved=path.parent/resolved
        assert resolved.exists(),(path,target)
        links.append({'source':str(path),'target':target})
sources={}
for name in ('tools/board_recording.py','tools/board_avatar_worker.py','tools/board_avatar_gtk.py',
             'tools/asr_server.py','tools/configure_board_asr.py','tools/package_board_avatar.py',
             'board/runtime/audio/transcription.py','common/asr_wire.py','tests/framework/test_transcription.py'):
    raw=(AURA/name).read_bytes();compile(raw,str(AURA/name),'exec')
    sources[name]=hashlib.sha256(raw).hexdigest()
result={'status':'PASS','verified_document_links':len(links),'python_sources':sources,
        'powershell_runtime_tested':False}
(WORK/'document_validation.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result))
