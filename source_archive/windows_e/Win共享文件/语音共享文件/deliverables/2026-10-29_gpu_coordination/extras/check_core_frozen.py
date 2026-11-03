import hashlib,json
from pathlib import Path
H=Path(__file__).resolve().parent
old=json.loads((H/'baseline.json').read_text())['core_candidate_sha256']
new=json.loads((H.parent/'SOURCE_MANIFEST.json').read_text())
actual={name:hashlib.sha256((H.parent/'candidate'/name).read_bytes()).hexdigest() for name in old}
assert all(actual[name]==new[name]['sha256'] for name in old)
changed=[name for name in old if actual[name]!=old[name]]
assert changed==['common/gpu_coordination.py'],changed
value={'status':'PASS','only_parent_authorized_core_file_changed':changed,'core_sha256':actual}
(H/'core_freeze_after_review.json').write_text(json.dumps(value,indent=2),encoding='utf-8')
print(json.dumps({'status':'PASS','gpu_coordination_sha256':actual['common/gpu_coordination.py'],'other_five_core_files_unchanged':True}))
