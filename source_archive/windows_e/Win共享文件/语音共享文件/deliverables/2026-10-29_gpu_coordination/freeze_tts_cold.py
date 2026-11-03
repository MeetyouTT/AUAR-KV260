import hashlib,json,shutil
from pathlib import Path
H=Path(__file__).resolve().parent
old=json.loads((H/'SOURCE_MANIFEST.json').read_text())
allowed={'common/gpu_coordination.py','tools/selected_voice_service.py'}
actual={name:hashlib.sha256((H/'candidate'/name).read_bytes()).hexdigest() for name in old}
changed={name for name in old if old[name]['sha256']!=actual[name]}
assert changed==allowed,changed
archive=H/'SOURCE_MANIFEST.before_tts_cold_review.json'
if not archive.exists():shutil.copy2(H/'SOURCE_MANIFEST.json',archive)
value={'status':'PASS','parent_authorized_changes':sorted(changed),'other_four_core_files_unchanged':True,'core_sha256':actual}
(H/'extras/core_freeze_after_tts_cold_review.json').write_text(json.dumps(value,indent=2),encoding='utf-8')
print(json.dumps({'status':'PASS','updated_sha256':{name:actual[name] for name in sorted(allowed)},'other_four_core_files_unchanged':True}))
