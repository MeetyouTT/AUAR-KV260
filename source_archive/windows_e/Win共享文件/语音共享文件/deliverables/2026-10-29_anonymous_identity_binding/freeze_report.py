"""Check and freeze this isolated candidate, without importing project code."""
import datetime,hashlib,json,xml.etree.ElementTree as ET
from pathlib import Path

H=Path(__file__).resolve().parent
B=H.parent/'2026-10-29_speaker_visual_cooperation'
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def write(name,value):
    (H/name).write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
base={
 'common/speaker_turns.py':json.loads((H/'v1_evidence_baseline.json').read_text(encoding='utf-8')),
 'tools/speaker_turns.py':json.loads((H/'hub_adapter_base.json').read_text(encoding='utf-8'))}
files={};compiled=[]
for path in sorted((H/'candidate').rglob('*')):
    if not path.is_file() or path.suffix not in ('.py','.json'):continue
    name=path.relative_to(H/'candidate').as_posix()
    raw=path.read_bytes()
    if path.suffix=='.py':compile(raw,str(path),'exec');compiled.append(name)
    else:json.loads(raw.decode('utf-8'))
    origin=base.get(name)
    if origin is not None:
        assert sha(Path(origin['source']))==origin['sha256'],'Base changed: '+name
        if name=='common/speaker_turns.py':assert raw.startswith(Path(origin['source']).read_bytes()),'Original v1 bytes changed'
    files[name]=dict(sha256=sha(path),bytes=len(raw),base_sha256=origin['sha256'] if origin else None)
tests={}
for key,filename in [('specialized','tests.xml'),('compatibility','compat_tests.xml')]:
    suite=ET.parse(H/filename).getroot().find('testsuite')
    item={name:int(suite.attrib[name]) for name in ('tests','failures','errors','skipped')}
    assert item['failures']==item['errors']==item['skipped']==0
    item.update(seconds=float(suite.attrib['time']),xml_sha256=sha(H/filename));tests[key]=item
created=datetime.datetime.now(datetime.timezone.utc).isoformat()
manifest=dict(version=1,status='CANDIDATE_VERIFIED_INTEGRATION_REQUIRED',created_utc=created,files=files,
 base_manifest_sha256=sha(B/'SOURCE_MANIFEST.json'),base_increments=base,compiled=compiled,tests=tests,
 constraints=dict(production_source_edited=False,deployed=False,real_identity_records_accessed=False,real_accuracy_accepted=False,
    microphone_enabled=False,speaker_playback=False,motion=False,new_models_loaded=False,llm_storage_changed=False),
 required_parent_hooks=['Hub single CPU worker initializer/private stores','ModelHandler pre-device binding route and skip flag',
    'BindingIdentityReplyStream owner/token wire bridge','Board authorized enrollment text translation',
    'Real face COMMITTED/gallery metadata readback and restricted receipt signing','Original identity deletion/revocation sync',
    'Final source pins and runtime deployment verification','Concentrated human calibration and identity tests'])
write('SOURCE_MANIFEST.json',manifest)
write('PROGRESS.json',dict(version=1,status=manifest['status'],updated_utc=created,candidate_verified=True,complete=False,
 production_deployed=False,human_accuracy_verified=False,tests=tests,candidate_files=len(files),
 manifest_sha256=sha(H/'SOURCE_MANIFEST.json'),remaining=manifest['required_parent_hooks']))
write('compile_verified.json',dict(ok=True,compiled=len(compiled),json_files=len(files)-len(compiled),
 originals_v1_bytes_preserved=True,increment_bases_match_current_frozen_sources=True))
print(json.dumps(dict(status=manifest['status'],candidate_files=len(files),compiled=len(compiled),tests=tests),ensure_ascii=False))
