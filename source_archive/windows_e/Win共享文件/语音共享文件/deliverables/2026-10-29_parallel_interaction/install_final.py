"""Controlled project-only restart and reversible final source transaction."""
import datetime,hashlib,json,os,runpy,socket,subprocess,sys,time,uuid,xml.etree.ElementTree as ET
from pathlib import Path
H=Path(__file__).resolve().parent;P=H.parents[1];A=P/'aura'
sys.path[:0]=[str(H.parent/'2026-10-29_audio_animation_polish'),str(H.parent/'2026-10-29_service_recovery')]
from board_guard import capture,same
from recovery_common import checkpoint
import urllib.request
assert not (H/'final_installation.json').exists(),'Preserve prior deployment evidence'
suite=ET.parse(H/'final_tests.xml').getroot()
assert sum(int(n.get('tests',0)) for n in suite.iter('testsuite'))>=637
assert all(int(n.get('failures',0))==0 and int(n.get('errors',0))==0 for n in suite.iter('testsuite'))
manifest=json.loads((H/'final_manifest.json').read_text(encoding='utf-8'))
board=json.loads((H/'board_preflight.json').read_text(encoding='utf-8'))
def http(url):
    with urllib.request.urlopen(url,timeout=4) as r:return json.load(r)
def ps(*args):
    result=subprocess.run(['powershell.exe','-NoProfile','-NonInteractive','-ExecutionPolicy','Bypass','-File',str(H/'reload_owned_service.ps1'),*args],capture_output=True,timeout=20)
    if result.returncode:raise RuntimeError((result.stdout+result.stderr).decode('utf-8-sig',errors='replace')[-1600:])
    return result.stdout.decode('utf-8-sig',errors='replace')
def check_sources():
    for name,item in manifest['files'].items():
        path=A/name;current=hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None
        assert current==item['current_before_sha256'],('Concurrent source update',name)
        assert hashlib.sha256((H/'final/aura'/name).read_bytes()).hexdigest()==item['sha256'],name
def idle():
    voice=http('http://192.168.50.1:8792/health');hub=http('http://127.0.0.1:8812/health')
    assert voice['ready'] and not voice['busy'] and voice['service_revision']=='voice-speaker-gpu-20261029-r10'
    assert not any(voice['gpu_coordination']['active'].values()) and voice['gpu_coordination']['queued']==0
    assert voice['speaker_attribution']['active_jobs']==0 and voice['speaker_attribution']['queued']==0
    assert hub['speaker_ready']
    same(board,capture());return voice,hub
idle();time.sleep(.6);idle();check_sources()
owner_module=runpy.run_path(str(P/'deliverables/2026-10-18_board_dialogue/project_ollama.py'))
record=json.loads((P/'deliverables/2026-10-18_board_dialogue/project_ollama_process.json').read_text(encoding='utf-8'))
owner=owner_module['inspect_ownership']();assert owner_module['ownership_matches'](record,owner)
private=checkpoint('before');(H/'private_before_final.json').write_text(json.dumps(private,indent=2),encoding='utf-8')
idle();check_sources()
report=dict(status='PREPARED',started_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
    revision=manifest['revision'],fingerprint=manifest['fingerprint'],files=manifest['files'],
    other_model_processes_stopped=False,other_models_unloaded=False,llm_weights_moved=False,
    microphone_enabled=False,physical_playback=False,motion_command_sent=False,project_daemon_restarted=False)
def save():(H/'final_installation.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
save();written=[];stopped=[]
try:
    for port in (8792,8812):
        report['stop_'+str(port)]=ps('-Port',str(port),'-StopOnly');stopped.append(port);save()
    for port in stopped:
        with socket.socket() as s:s.settimeout(.5);assert s.connect_ex(('192.168.50.1',port))!=0
    assert owner_module['ownership_matches'](record,owner_module['inspect_ownership']())
    # Only the controlled project's own expired cache is released. The API
    # defers actual destruction if a direct external client still has a ref;
    # this controller never kills a runner or asserts global no-inflight.
    research=H.parent/'2026-10-29_conversation_research/candidate/tools';sys.path.insert(0,str(research))
    api_module=runpy.run_path(str(research/'startup_vram.py'));api=api_module['FixedProjectOllamaApi']()
    deadline=time.monotonic()+30;api.unload('aura-qwen3.8-27b-abliterated:iq4_xs',deadline=deadline)
    while time.monotonic()<deadline:
        if not api.ps(deadline=deadline):break
        time.sleep(.1)
    else:raise TimeoutError('Own project cache still active; no runner killed')
    report['only_project_cache_released']=True;report['global_no_inflight_claimed']=False
    check_sources()
    for name,item in manifest['files'].items():
        target=A/name;backup=H/'final_source_before'/name
        if target.exists():backup.parent.mkdir(parents=True,exist_ok=True);backup.write_bytes(target.read_bytes())
        target.parent.mkdir(parents=True,exist_ok=True);raw=(H/'final/aura'/name).read_bytes()
        tmp=target.with_name(target.name+'.r11-'+uuid.uuid4().hex);tmp.write_bytes(raw);os.replace(tmp,target);written.append(name)
    capabilities=runpy.run_path(str(A/'common/voice_service_capabilities.py'))
    assert capabilities['source_fingerprint'](A)==manifest['fingerprint']
    report['status']='INSTALLED_FINAL';save()
except Exception as exc:
    report.update(status='INSTALL_FAILED',error=type(exc).__name__+': '+str(exc))
    for name in reversed(written):
        target=(A/name).resolve();target.relative_to(A.resolve());item=manifest['files'][name]
        assert hashlib.sha256(target.read_bytes()).hexdigest()==item['sha256'],'Concurrent rollback source change'
        if item['current_before_sha256'] is None:target.unlink()
        else:
            raw=(H/'final_source_before'/name).read_bytes();assert hashlib.sha256(raw).hexdigest()==item['current_before_sha256']
            tmp=target.with_name(target.name+'.restore-'+uuid.uuid4().hex);tmp.write_bytes(raw);os.replace(tmp,target)
    report['sources_restored']=True;save();raise
finally:
    for port in reversed(stopped):
        try:report['start_'+str(port)]=ps('-Port',str(port))
        except Exception as exc:report['start_error_'+str(port)]=str(exc)
    save()
print(json.dumps({k:report.get(k) for k in ('status','revision','fingerprint','only_project_cache_released','other_models_unloaded','start_error_8792','start_error_8812')}))
