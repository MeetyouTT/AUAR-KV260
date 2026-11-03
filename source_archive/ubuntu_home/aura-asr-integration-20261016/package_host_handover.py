"""Freeze the four missing Windows ASR files with per-file checksums."""
import hashlib
import json
from pathlib import Path
import socket
import zipfile

AURA=Path('/home/ghmd/Win共享文件/共享文件夹/aura')
OUT=AURA.parent/'deliverables/2026-10-17_board_asr_host_files'
names=('scripts/start_board_asr.ps1','tools/asr_server.py','common/asr_wire.py','docs/BOARD_ASR.md')
files={name:(AURA/name).read_bytes() for name in names}
rows={name:{'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()} for name,raw in files.items()}
release=hashlib.sha256(json.dumps(rows,sort_keys=True).encode()).hexdigest()[:16]
manifest={'release_id':release,'source_host':socket.gethostname(),'source_root':str(AURA),
          'extract_into':'Windows project aura directory','files':rows,
          'models_and_python_environment_included':False}
OUT.mkdir(parents=True,exist_ok=True)
archive=OUT/('asr-host-files-'+release+'.zip')
with zipfile.ZipFile(archive,'x',compression=zipfile.ZIP_DEFLATED) as z:
    for name,raw in files.items():z.writestr(name,raw)
    z.writestr('ASR_HOST_FILES_MANIFEST.json',json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
with zipfile.ZipFile(archive) as z:
    assert z.testzip() is None
    assert set(z.namelist())==set(names)|{'ASR_HOST_FILES_MANIFEST.json'}
    for name,raw in files.items():assert z.read(name)==raw
record={'status':'PASS_FOUR_SOURCE_FILES_READBACK','archive':str(archive),'bytes':archive.stat().st_size,
        'sha256':hashlib.sha256(archive.read_bytes()).hexdigest(),'manifest':manifest}
(OUT/'verification.json').write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(record,ensure_ascii=False))
