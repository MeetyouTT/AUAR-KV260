"""Controlled project-only layout experiment. No other model management APIs."""
import argparse,datetime,hashlib,json,runpy,socket,subprocess,sys,time,urllib.request
from pathlib import Path
H=Path(__file__).resolve().parent;P=H.parents[1];A=P/'aura'
sys.path[:0]=[str(A),str(H.parent/'2026-10-29_audio_animation_polish')]
from board_guard import capture,same
from common.gpu_coordination import NvidiaMemoryProbe
p=argparse.ArgumentParser();p.add_argument('--phase',default='initial');p.add_argument('--target-mib',type=int);args=p.parse_args()
assert args.phase.replace('_','').isalnum()
result_path=H/('layout_applied.json' if args.phase=='initial' else 'layout_applied_'+args.phase+'.json')
assert not result_path.exists()
before=json.loads((H/'runtime_owners_before.json').read_text(encoding='utf-8-sig'))
module=runpy.run_path(str(P/'deliverables/2026-10-18_board_dialogue/project_ollama.py'))
plan=json.loads((H/'layout_plan.json').read_text(encoding='utf-8'))
assert plan['status']=='PREPARED_NOT_APPLIED'
def http(url,value=None,timeout=5):
    request=urllib.request.Request(url,data=json.dumps(value).encode() if value is not None else None,
      headers={'Content-Type':'application/json'} if value is not None else {})
    with urllib.request.urlopen(request,timeout=timeout) as r:return json.load(r)
def ps(name,*args):
    r=subprocess.run(['powershell.exe','-NoProfile','-NonInteractive','-ExecutionPolicy','Bypass','-File',str(H/name),*args],capture_output=True,timeout=15)
    if r.returncode:raise RuntimeError((r.stdout+r.stderr).decode('utf-8-sig',errors='replace')[-1200:])
    return r.stdout.decode('utf-8-sig',errors='replace')
expected_owner=before['11435']
def owner_matches():
    current=module['inspect_ownership']();old=before['11435']
    old=expected_owner
    assert current['pid']==old['pid'] and current['executable']==old['exe'] and current['command_line']==old['command_line']
    assert datetime.datetime.fromisoformat(current['creation_utc'].replace('Z','+00:00'))==datetime.datetime.fromisoformat(old['creation_utc'].replace('Z','+00:00'))
    return current
if args.phase!='initial':
    existing=json.loads((P/'deliverables/2026-10-18_board_dialogue/project_ollama_process.json').read_text(encoding='utf-8'))
    current=module['inspect_ownership']();assert module['ownership_matches'](existing,current),'Daemon is no longer the created project instance'
    assert hashlib.sha256(Path(current['executable']).read_bytes()).hexdigest()==existing['bindings']['executable_sha256']
    expected_owner=dict(pid=current['pid'],creation_utc=current['creation_utc'],exe=current['executable'],command_line=current['command_line'])
    assert args.target_mib is not None and 128<=args.target_mib<16311
    canonical=P/'aura/config/ollama_runtime.local.json';prior=canonical.read_bytes()
    assert hashlib.sha256(prior).hexdigest()==existing['runtime_policy']['config_sha256']
    (H/('layout_config_before_'+args.phase+'.json')).write_bytes(prior)
    policy=json.loads(prior);policy['fit_target_mib']=args.target_mib;policy['calibration_id']='provisional-layout-probe-20261029-'+str(args.target_mib)+'m'
    canonical.write_text(json.dumps(policy,indent=2),encoding='utf-8');plan=dict(plan,policy=policy)
(H/'layout_stop_owner.json').write_text(json.dumps(expected_owner,indent=2),encoding='utf-8')
board=capture();assert board['safe'] and not board['mismatches'];time.sleep(.6);same(board,capture())
voice=http('http://192.168.50.1:8792/health');assert voice['ready'] and not voice['busy']
assert not any(voice['gpu_coordination']['active'].values()) and voice['gpu_coordination']['queued']==0
owner=owner_matches();model=json.loads((A/'config/board_dialogue_model.json').read_text())['model']
residency=http('http://127.0.0.1:11435/api/ps');assert all(row.get('name')==model or row.get('model')==model for row in residency['models'])
report=dict(status='PREPARED',phase='PROVISIONAL_LAYOUT_EXPERIMENT',owner_before=owner,policy=plan['policy'],
 other_models_unloaded=False,weights_deleted=False,databases_restored=False,microphone_enabled=False,motion_command_sent=False)
def save():result_path.write_text(json.dumps(report,indent=2),encoding='utf-8')
save();voice_stopped=False
try:
    report['voice_stop']=ps('reload_owned_service.ps1','-Port','8792','-StopOnly');voice_stopped=True
    with socket.socket() as s:s.settimeout(.5);assert s.connect_ex(('192.168.50.1',8792))!=0,'Voice server still accepting requests'
    owner_matches()
    reply=http('http://127.0.0.1:11435/api/generate',{'model':model,'keep_alive':0,'stream':False},timeout=10)
    assert reply.get('done') is True and reply.get('done_reason')=='unload'
    report['only_project_model_unloaded']=model;report['unload_generates_tokens']=False
    end=time.monotonic()+20;probe=NvidiaMemoryProbe()
    while time.monotonic()<end:
        empty=not http('http://127.0.0.1:11435/api/ps')['models'];memory=probe.read()
        if empty and memory.free_mib>=5255:break
        time.sleep(.2)
    else:raise RuntimeError('Project model release not observed; no daemon stopped')
    report['free_after_own_release_mib']=memory.free_mib
    owner_matches();report['daemon_stop']=ps('stop_project_daemon.ps1')
    receipt='layout_daemon_start.json' if args.phase=='initial' else 'layout_daemon_start_'+args.phase+'.json'
    report['daemon_launch']=ps('start_project_daemon.ps1','-Receipt',receipt)
    end=time.monotonic()+35
    while time.monotonic()<end:
        path=H/receipt
        if path.exists():
            result=json.loads(path.read_text(encoding='utf-8'))
            if result.get('status')=='STARTED':break
            if result.get('status')=='FAILED':raise RuntimeError(result.get('error','New project daemon failed'))
        time.sleep(.2)
    else:raise TimeoutError('Project daemon creation receipt timed out')
    assert result['launch_environment_applied'] and not result['effective_runner_budget_verified']
    report.update(status='APPLIED_NEEDS_MODEL_LOAD_VALIDATION',new_daemon=result,source_unchanged_27b=True,
      context_length=2048,fit_target_mib=plan['policy']['fit_target_mib'],actual_fit_effect_verified=False)
except Exception as exc:report.update(status='FAILED_NEEDS_RECOVERY',error=type(exc).__name__+': '+str(exc))
finally:
    save()
    # Always attempt to restore the owned voice service after the operation.
    if voice_stopped:
        try:report['voice_restart']=ps('reload_owned_service.ps1','-Port','8792')
        except Exception as exc:report['voice_restart_error']=type(exc).__name__+': '+str(exc)
    save()
print(json.dumps({k:report.get(k) for k in ('status','fit_target_mib','free_after_own_release_mib','other_models_unloaded','error','voice_restart_error')}))
raise SystemExit(0 if report['status']=='APPLIED_NEEDS_MODEL_LOAD_VALIDATION' else 1)
