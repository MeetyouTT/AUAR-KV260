"""Hash-checked final union; never writes the running source tree."""
import ast,hashlib,json
from pathlib import Path
H=Path(__file__).resolve().parent;P=H.parents[1];A=P/'aura';D=H.parent
sources={};origins={}
def take(root,manifest,origin,*,overrides=()):
    for name,item in manifest.items():
        raw=(root/name).read_bytes()
        assert hashlib.sha256(raw).hexdigest()==item['sha256'],(origin,name)
        if name in sources and sources[name]!=raw:
            assert name in overrides,('Unexpected candidate collision',origin,name)
        sources[name]=raw;origins[name]=origin
def manifest(path):
    value=json.loads(path.read_text(encoding='utf-8'));return value.get('files',value)
G=D/'2026-10-29_gpu_coordination';S=D/'2026-10-29_speaker_visual_cooperation'
N=D/'2026-10-29_anonymous_identity_binding';R=D/'2026-10-29_conversation_research'
take(G/'candidate',manifest(G/'SOURCE_MANIFEST.json'),'gpu88')
take(S/'candidate',manifest(S/'SOURCE_MANIFEST.json'),'speaker55')
take(N/'candidate',manifest(N/'SOURCE_MANIFEST.json'),'anonymous69',overrides=('common/speaker_turns.py','tools/speaker_turns.py'))
take(N/'extras/candidate',manifest(N/'extras/SOURCE_MANIFEST.json'),'binding-hub-integration',overrides=('tools/device_hub.py',))
take(S/'board_bridge/candidate',manifest(S/'board_bridge/SOURCE_MANIFEST.json'),'actual-dpu-readback',
     overrides=('board/runtime/audio/channel_jobs.py','board/runtime/audio/voice_channel.py','common/speaker_visual.py','common/binding_intent.py'))
startup=R/'extras/startup_guard'
startup_manifest=json.loads((startup/'manifest.json').read_text(encoding='utf-8'))
take(startup/'candidate',{row['path'][len('candidate/'):]:row for row in startup_manifest['files'] if row['path'].startswith('candidate/')},'cold-start-capacity')
lock=next(row for row in startup_manifest['dependencies'] if row['path'].endswith('service_instance_lock.py'))
take(R/'candidate',{'tools/service_instance_lock.py':lock},'lifetime-lock')
take(A,{'config/ollama_runtime.local.json':{'sha256':hashlib.sha256((A/'config/ollama_runtime.local.json').read_bytes()).hexdigest()}},'measured-actual-project-layout')
for root,label,overrides in [(H/'candidate/windows','parent-observation',('tools/board_model_host.py','tools/dialogue_host_ollama.py')),
                              (H/'candidate/final_parent','parent-final',('tools/board_model_host.py','tools/voice_channel_source.py','config/gpu_runtime.local.json'))]:
    for path in root.rglob('*'):
        if not path.is_file() or '__pycache__' in path.parts:continue
        name=path.relative_to(root).as_posix()
        if label=='parent-observation' and name=='config/gpu_runtime.local.json':continue
        if name in sources and sources[name]!=path.read_bytes():assert name in overrides,(label,name)
        sources[name]=path.read_bytes();origins[name]=label
name='common/voice_service_capabilities.py'
s=(H/'source_before'/name).read_text(encoding='utf-8')
assert "SERVICE_REVISION = 'voice-chat-memory-20261029-r9'" in s
s=s.replace("SERVICE_REVISION = 'voice-chat-memory-20261029-r9'","SERVICE_REVISION = 'voice-identity-gpu-20261030-r11'")
tree=ast.parse(s);cap=next(n for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='CAPABILITIES' for t in n.targets))
caps=ast.literal_eval(cap.value);caps.update(gpu_phase_coordination=1,calibrated_gpu_admission=1,cold_tts_capacity_preflight=1,
    turn_speaker_observation=1,optional_face_observation=1,anonymous_speaker_timeline=1,explicit_face_voice_binding=1,original_gallery_revocation=1)
lines=s.splitlines(keepends=True);lines[cap.lineno-1:cap.end_lineno]=['CAPABILITIES = '+repr(caps)+'\n'];s=''.join(lines)
node=next(n for n in ast.parse(s).body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='SOURCE_FILES' for t in n.targets))
old=ast.literal_eval(node.value);names=tuple(sorted(set(old)|set(sources)))
lines=s.splitlines(keepends=True);lines[node.lineno-1:node.end_lineno]=['SOURCE_FILES = (\n',*['    '+repr(n)+',\n' for n in names],')\n'];s=''.join(lines)
sources[name]=s.encode();origins[name]='parent-final-version'
out=H/'final/aura';rows={}
for name,raw in sources.items():
    target=out/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(raw)
    if name.endswith('.py'):compile(raw,name,'exec')
    rows[name]=dict(sha256=hashlib.sha256(raw).hexdigest(),bytes=len(raw),origin=origins[name],
        current_before_sha256=hashlib.sha256((A/name).read_bytes()).hexdigest() if (A/name).is_file() else None)
def fingerprint():
    digest=hashlib.sha256()
    for name in names:
        digest.update(name.encode()+b'\0');digest.update(hashlib.sha256(sources[name] if name in sources else (A/name).read_bytes()).digest())
    return digest.hexdigest()
report=dict(status='STAGED_FINAL_NOT_DEPLOYED',files=rows,revision='voice-identity-gpu-20261030-r11',fingerprint=fingerprint())
(H/'final_manifest.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps({k:report[k] for k in ('status','revision','fingerprint')}|{'files':len(rows)}))
