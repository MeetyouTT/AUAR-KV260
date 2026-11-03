import datetime,hashlib,json,shutil
from pathlib import Path
H=Path(__file__).resolve().parent;P=H.parents[2]
source=P/'deliverables/2026-10-18_board_dialogue/project_ollama.py'
assert source.is_file() and not (H/'baseline.json').exists()
backup=H/'before/project_ollama.py';backup.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,backup)
core=json.loads((H.parent/'SOURCE_MANIFEST.json').read_text())
assert all(hashlib.sha256((H.parent/'candidate'/name).read_bytes()).hexdigest()==value['sha256'] for name,value in core.items())
value={'checked_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'source':str(source),
 'sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'bytes':source.stat().st_size,
 'core_candidate_sha256':{name:value['sha256'] for name,value in core.items()},'core_frozen':True}
(H/'baseline.json').write_text(json.dumps(value,indent=2),encoding='utf-8');print(json.dumps({'status':'RECORDED','sha256':value['sha256'],'core_files':len(core)}))
