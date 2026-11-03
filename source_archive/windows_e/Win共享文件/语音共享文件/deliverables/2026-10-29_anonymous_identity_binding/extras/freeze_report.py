"""Freeze extras only; verify original 14 candidates stayed byte-identical."""
import datetime,hashlib,json,xml.etree.ElementTree as ET
from pathlib import Path
H=Path(__file__).resolve().parent;P=H.parent;B=P.parent/'2026-10-29_speaker_visual_cooperation'
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def write(name,value):(H/name).write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
core=json.loads((P/'SOURCE_MANIFEST.json').read_text(encoding='utf-8'))
for name,row in core['files'].items():assert sha(P/'candidate'/name)==row['sha256'],'Frozen core changed: '+name
base=json.loads((H/'hub_base.json').read_text(encoding='utf-8'));assert sha(Path(base['source']))==base['sha256']
codec=B/'board_bridge/candidate/common/face_binding_wire.py';assert codec.is_file()
files={}
for path in sorted((H/'candidate').rglob('*.py')):
    compile(path.read_bytes(),str(path),'exec');name=path.relative_to(H/'candidate').as_posix()
    files[name]=dict(sha256=sha(path),bytes=path.stat().st_size,base_sha256=base['sha256'] if name=='tools/device_hub.py' else None)
tests={}
for name,xmlfile in [('extras','tests.xml'),('core_compatibility_under_extras','regression_tests.xml')]:
    suite=ET.parse(H/xmlfile).getroot().find('testsuite');item={key:int(suite.attrib[key]) for key in ('tests','failures','errors','skipped')}
    assert item['failures']==item['errors']==item['skipped']==0
    item.update(seconds=float(suite.attrib['time']),xml_sha256=sha(H/xmlfile));tests[name]=item
created=datetime.datetime.now(datetime.timezone.utc).isoformat()
manifest=dict(version=1,status='CANDIDATE_VERIFIED_NOT_DEPLOYED',created_utc=created,candidate_root=str(H/'candidate'),files=files,
  overwrite_allowlist=['tools/device_hub.py'],core_manifest_sha256=sha(P/'SOURCE_MANIFEST.json'),core_14_verified_unchanged=True,
  hub_base=base,dependencies={'common/face_binding_wire.py':dict(source=str(codec),sha256=sha(codec))},tests=tests,
  compiled_python_files=len(files),boundaries=dict(identity_result_max_bytes=4096,gallery_body_max_bytes=24576,
  typed_binding_client='loopback_only',encoder='existing_single_CPU_worker',profile_grants=False),
  constraints=dict(production_source_edited=False,deployed=False,real_templates_accessed=False,new_models_loaded=False,microphone_enabled=False,playback=False,motion=False))
write('SOURCE_MANIFEST.json',manifest)
write('PROGRESS.json',dict(version=1,status=manifest['status'],updated_utc=created,complete=False,candidate_verified=True,
  manifest_sha256=sha(H/'SOURCE_MANIFEST.json'),tests=tests,remaining=['Parent final union/pins and deployment','Board real bridge final verification','Concentrated human identity calibration']))
print(json.dumps(dict(status=manifest['status'],files=len(files),tests=tests),ensure_ascii=False))
