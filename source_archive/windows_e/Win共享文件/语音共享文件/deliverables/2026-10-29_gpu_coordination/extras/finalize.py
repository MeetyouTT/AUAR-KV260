import datetime,hashlib,json,xml.etree.ElementTree as ET
from pathlib import Path
H=Path(__file__).resolve().parent;P=H.parents[2]
suite=ET.parse(H/'tests.xml').getroot().find('testsuite');assert suite is not None
assert suite.attrib['failures']=='0' and suite.attrib['errors']=='0'
baseline=json.loads((H/'baseline.json').read_text());freeze=json.loads((H/'core_freeze_after_review.json').read_text())['core_sha256']
assert all(hashlib.sha256((H.parent/'candidate'/name).read_bytes()).hexdigest()==sha for name,sha in freeze.items())
assert hashlib.sha256(Path(baseline['source']).read_bytes()).hexdigest()==baseline['sha256']
files={}
for path in (H/'candidate').rglob('*'):
    if path.is_file():
        if path.suffix=='.py':compile(path.read_text(encoding='utf-8'),str(path),'exec')
        files[path.relative_to(H/'candidate').as_posix()]={'bytes':path.stat().st_size,'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
compile((H/'inspect_restart_ownership.py').read_text(encoding='utf-8'),'inspector','exec')
(H/'SOURCE_MANIFEST.json').write_text(json.dumps(files,indent=2),encoding='utf-8')
report={'status':'STARTUP_CANDIDATE_READY_NOT_APPLIED','checked_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
 'tests':{key:int(suite.attrib[key]) for key in ('tests','failures','errors','skipped')},'core_six_candidates_frozen':True,
 'original_project_ollama_sha256':baseline['sha256'],'original_project_ollama_unchanged':True,
 'real_restart_or_model_loading_performed':False,'production_fit_target_specified':False,
 'configuration_changes_require_controlled_restart':True,'physical_vram_isolation_or_effective_fit_verified':False}
(H/'PROGRESS.json').write_text(json.dumps(report,indent=2),encoding='utf-8');print(json.dumps(report))
