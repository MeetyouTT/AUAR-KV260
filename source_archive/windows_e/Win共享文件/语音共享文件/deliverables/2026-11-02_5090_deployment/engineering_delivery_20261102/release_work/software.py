from common import *
import ast,re
ci=ROOT/'src/camera'
cam=P/'deliverables/2026-10-24_native_critical_live'
base=load(cam/'release.json')
for n,h in base['files_sha256'].items():
    p=cam/'source/aura'/n
    if not p.is_file() or sha(p)!=h:raise RuntimeError('camera baseline: '+n)
    copy(p,ci/'runtime'/n)
save(ci/'release_r4.json',base)
audit=B/'cpu_optimization_20261102/camera'
rows={}
for n,get in [('SOURCE_DISCOVERY',lambda j:j['board_result']['source_files']),('EXTRA_SOURCE_MANIFEST',lambda j:j['source_files']),('INGRESS_SOURCE_MANIFEST',lambda j:j['source_files'])]:
    for r in get(load(audit/(n+'.json'))):
        path=r['path'];h=r['sha256'];name=Path(path).name
        f=Path(r['local_path']) if r.get('local_path') else audit/'baseline'/(h[:12]+'__'+name)
        if not f.is_file():f=audit/'baseline'/(h[:12]+'__'+name)
        if sha(f)!=h:raise RuntimeError(str(f))
        if '/native-r4-metrics-fix/aura/' in path:dest=ci/'runtime'/path.split('/native-r4-metrics-fix/aura/')[1]
        elif '/pan-face-edge-v5/' in path:dest=ci/'entry_chain'/path.split('/pan-face-edge-v5/')[1]
        else:dest=ci/'entry_chain'/name
        copy(f,dest)
        rows[path]={'path':dest.relative_to(ROOT).as_posix(),'sha256':h}
for row in load(B/'axis_follow_restore/source_index.json').items():
    path,r=row
    if not (path.endswith('.py') and ('/pan-face-edge-v5/' in path or path.endswith(('/boot_ops.py','/native_entry.py','/policy.py')))):continue
    relative=path.split('/pan-face-edge-v5/')[1] if '/pan-face-edge-v5/' in path else path.rsplit('/',1)[1]
    p=Path(r['local_path']);dest=ci/'entry_chain'/relative
    if dest.exists():
        continue
    assert sha(p)==r['sha256'];copy(p,dest);rows[path]={'path':dest.relative_to(ROOT).as_posix(),'sha256':r['sha256']}
save(ci/'entry_chain/source_paths.json',rows)
save(ci/'reference_config.json',load(audit/'SOURCE_DISCOVERY.json')['board_result']['config'])
for n,h in load(audit/'NATIVE_UNIT_PROVENANCE.json')['unit_manifest']['files'].items():
    assert sha(ci/'native_operator'/n)==h, n
copy(audit/'NATIVE_UNIT_PROVENANCE.json',ci/'native_operator/build_provenance.json')
ed=B/'cpu_optimization_20261102/visual_artifact_fix_20261102/editor_layout_only/face_zone_editor.py'
copy(ed,ROOT/'src/motion/editor/face_zone_editor.py')
d=B/'maintenance_original_axis_20261101/left_stop40_20261102/recovery_stability_20261102_v3'
rc=d/'candidate'; mp=rc/'deployment-manifest.json'
actual=load(ROOT/'src/software/config/pan_face.local.json')
m=load(mp)
lookup=d.parent
for script in [lookup/'apply_left40_right45.prepared.py',lookup/'py39_fix/apply_py39_fix.prepared.py',d/'apply_stable150.prepared.py']:
    line=next(l for l in script.read_text(encoding='utf-8').splitlines() if l.startswith("candidate_manifest['scope']="))
    suffix=ast.literal_eval(line.split("manifest['scope']+",1)[1])
    m['scope']+=suffix
for r in m['files']:
    n=r['source_rel'];p=rc/n
    r.update(destination=actual['release_root']+'/'+n,sha256=sha(p),bytes=p.stat().st_size)
    copy(p,ROOT/'src/motion/follow'/n)
mp=ROOT/'src/motion/follow/deployment-manifest.json'
mp.write_bytes((json.dumps(m,sort_keys=True,indent=2)+'\n').encode())
assert sha(mp)==actual['manifest_sha256'],sha(mp)
copy(d/'APPLIED.json',ROOT/'data/results/motion_publication.json')
for p in [d/'test_rearm_stability.py',d/'test_left_episode.py',d/'run_pure_suite.py']:copy(p,ROOT/'sim/motion'/p.name)
# Yuki runtime, exact host bindings and only CMake-referenced upstream components.
y=P/'deliverables/2026-10-30_yuki_native_validation'
yd=ROOT/'src/avatar'
for sub in ['deps','native_integration/candidate_core/src','native_integration/candidate_core/include','native_integration/candidate_core/tools','native_integration/third_party_licenses']:
    for p in (y/sub).rglob('*'):
        if p.is_file() and '__pycache__' not in p.parts:copy(p,yd/p.relative_to(y))
for sub in ['native_integration/host','native_integration/precision_candidate']:
    for p in (y/sub).iterdir():
        if p.suffix in ['.cpp','.h','.hpp'] or p.name=='CMakeLists.txt':copy(p,yd/p.relative_to(y))
for n in ['agent_audit/frame_export.cpp','native_integration/candidate_core/LICENSE','dependency-provenance.json','asset-provenance.json','source-provenance.json']:copy(y/n,yd/n)
# Windows code has path-relative dependencies, retain the deployed project-relative structure.
wd=ROOT/'src/windows'
h='deliverables/2026-10-30_board_owner/integration/production_model_host'
for n in ['production_runtime.py','manage.py','test_production_runtime.py','README.txt']:
    copy(P/h/n,wd/h/n)
for n in ['start_inference.ps1','deliverables/2026-10-18_board_dialogue/project_ollama.py']:
    copy(P/n,wd/n)
for sub in ['common','tools','board','host']:
    for p in (P/'aura'/sub).rglob('*.py'):
        if '.sync-conflict-' not in p.name and '__pycache__' not in p.parts:
            copy(p,wd/'aura'/p.relative_to(P/'aura'))
for n in ['model_inference.local','board_dialogue_model','model_storage.local','gpu_runtime.local','ollama_runtime.local']:
    copy(P/'aura/config'/(n+'.json'),wd/'aura/config'/(n+'.json'))
copy(B/'voice_py310_requirements_5090.txt',wd/'requirements-5090.txt')
copy(Path(r'D:\AIModels\qwen3.8-27b-abliterated\Modelfile'),wd/'modelfile.txt')
copy(B/'llm_download_verification.json',ROOT/'models/host_llm.json')
copy(P/'aura/models/tts/OmniVoice/download_identity.json',ROOT/'models/host_tts.json')
oe=SH/'5090主机迁移包_20261101/external_dependencies/source'
for p in (oe/'omnivoice').rglob('*'):
    if p.is_file() and p.suffix in ('.py','.json','.yaml','.yml','.txt') and '__pycache__' not in p.parts:
        copy(p,wd/'omnivoice_source'/p.relative_to(oe))
copy(oe/'pyproject.toml',wd/'omnivoice_source/pyproject.toml')
for p in (P/'aura/scripts/board_ui_startup').glob('*'):
    if p.is_file() and (p.name in ['aura-avatar-ui.service.in','launcher.py']):copy(p,ROOT/'board/startup'/p.name)
for p in (P/'deliverables/2026-10-21_dpu_vision_start/source').glob('*.py'):copy(p,ROOT/'src/vision_quantization'/p.name)
print('Camera source',len(base['files_sha256']),'+',len(rows) if isinstance(rows,dict) else 'entry overlay','; motion',len(m['files']),'; control publisher hash',sha(mp))
