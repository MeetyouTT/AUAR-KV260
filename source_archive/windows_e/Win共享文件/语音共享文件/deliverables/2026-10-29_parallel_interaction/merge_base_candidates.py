"""Reviewable union of frozen subagent candidates plus parent-owned hooks."""
import ast,hashlib,json,shutil
from pathlib import Path
H=Path(__file__).resolve().parent;P=H.parents[1];A=P/'aura'
G=H.parent/'2026-10-29_gpu_coordination';S=H.parent/'2026-10-29_speaker_visual_cooperation'
sources={};provenance={}
gm=json.loads((G/'SOURCE_MANIFEST.json').read_text(encoding='utf-8'))
sm=json.loads((S/'SOURCE_MANIFEST.json').read_text(encoding='utf-8'))['files']
for label,root,manifest in [('gpu',G,gm),('speaker',S,sm)]:
    for name,item in manifest.items():
        raw=(root/'candidate'/name).read_bytes();assert hashlib.sha256(raw).hexdigest()==item['sha256'],name
        assert name not in sources,('Unexpected candidate collision',name)
        sources[name]=raw;provenance[name]=label
for path in (H/'candidate/windows').rglob('*'):
    if not path.is_file():continue
    name=path.relative_to(H/'candidate/windows').as_posix()
    if name=='config/gpu_runtime.local.json':continue
    sources[name]=path.read_bytes();provenance[name]='parent'
name='common/voice_service_capabilities.py';original=(A/name).read_bytes();text=original.decode('utf-8')
assert "SERVICE_REVISION = 'voice-chat-memory-20261029-r9'" in text
text=text.replace("SERVICE_REVISION = 'voice-chat-memory-20261029-r9'","SERVICE_REVISION = 'voice-speaker-gpu-20261029-r10'")
text=text.replace("CAPABILITIES = {", "CAPABILITIES = {'gpu_phase_coordination':1,'turn_speaker_observation':1,'optional_face_observation':1,")
tree=ast.parse(text);node=next(node for node in tree.body if isinstance(node,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='SOURCE_FILES' for t in node.targets))
existing=ast.literal_eval(node.value)
extra=tuple(sorted(name for name in sources if name not in existing))
marker="    'common/voice_admission.py',";assert text.count(marker)==1
text=text.replace(marker,''.join('    '+repr(name)+',\n' for name in extra)+marker)
sources[name]=text.encode();provenance[name]='parent-version-and-fingerprint'
before=H/'source_before'/name
if before.exists():assert before.read_bytes()==original
else:before.parent.mkdir(parents=True,exist_ok=True);before.write_bytes(original)
manifest={}
for name,raw in sources.items():
    target=H/'merged/aura'/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(raw)
    if name.endswith('.py'):compile(raw,name,'exec')
    manifest[name]=dict(bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest(),origin=provenance[name],
       current_before_sha256=hashlib.sha256((A/name).read_bytes()).hexdigest() if (A/name).exists() else None)
(H/'merged_manifest.json').write_text(json.dumps({'status':'MERGED_FOR_OBSERVATION_CALIBRATION','production_changed':False,
 'new_anonymous_binding_not_yet_integrated':True,'files':manifest},indent=2),encoding='utf-8')
print(json.dumps({'status':'MERGED','files':len(manifest),'production_changed':False,'gpu_mode':'observe'}))
