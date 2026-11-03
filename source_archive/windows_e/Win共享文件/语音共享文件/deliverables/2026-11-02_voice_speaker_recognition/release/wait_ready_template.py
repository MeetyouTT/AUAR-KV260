"""GET-only readiness after the single normal start; never resubmit start."""
import hashlib
import http.client
import json
from pathlib import Path
import subprocess
import time

E=None  # VOICE_READY_EXPECTED
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def unit(name):
    r=subprocess.run(['systemctl','show',name,'--property=MainPID,ActiveState,SubState,Job,Result,ExecMainStatus,Restart,KillMode,SendSIGKILL,TimeoutStopUSec'],capture_output=True,text=True,timeout=4);assert r.returncode==0
    return dict(x.split('=',1) for x in r.stdout.splitlines() if '=' in x)
def owner(pid):
    p=Path('/proc')/str(pid)
    return {'pid':int(pid),'birth_ticks':p.joinpath('stat').read_text().rsplit(')',1)[1].split()[19],'command_sha256':sha(p/'cmdline')}
def ui():
    c=http.client.HTTPConnection('127.0.0.1',8783,timeout=2)
    try:c.request('GET','/api/state');r=c.getresponse();raw=r.read(2097153);assert r.status==200 and len(raw)<=2097152;return json.loads(raw)
    finally:c.close()

assert isinstance(E,dict);assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==E['boot_id'];assert sha(E['startup_path'])==E['startup_sha256']
out={'schema':'aura-per-utterance-voice-post-start-ready-1','control_writes':0,'ready':False};end=time.monotonic()+45;v={}
while time.monotonic()<end:
    gu=unit('aura-avatar-ui.service')
    if gu['ActiveState']=='failed':break
    if gu['ActiveState']=='active' and gu['SubState']=='running' and int(gu['MainPID'])>0:
        try:
            v=ui();speaker=(v.get('board_business') or {}).get('speaker') or {};address=speaker.get('conversation_address') or {}
            if v.get('ui_page')=='main' and (v.get('avatar_display') or {}).get('visible') and (v.get('character_pair') or {}).get('state')=='READY' and speaker.get('ready') and address.get('mode')=='PER_UTTERANCE':out['ready']=True;break
        except (OSError,ValueError,AssertionError):pass
    time.sleep(.5)
cfg=json.loads(Path(E['startup_path']).read_bytes());launch=json.loads((Path(cfg['runtime'])/'launch.json').read_bytes());gu=unit('aura-avatar-ui.service');out['GUI_unit']=gu
out['camera_owner_unchanged']=owner(E['camera_owner']['pid'])==E['camera_owner'];out['startup_sha256']=sha(E['startup_path']);out['source_unchanged']=out['startup_sha256']==E['startup_sha256']
if out['ready']:
    assert launch['supervisor_pid']==int(gu['MainPID']) and launch['boot_id']==E['boot_id']
    out['gui_owner']=owner(launch['supervisor_pid']);out['gtk_owner']=owner(launch['pid']);out['camera_owner']=E['camera_owner']
    out['GUI_properties_restored']={k:gu[k] for k in E['original_GUI_properties']}==E['original_GUI_properties'];assert out['GUI_properties_restored']
    h=v['handsfree_dialogue'];speaker=v['board_business']['speaker'];pan=v['manual_pan'];rb=pan.get('readback') or {}
    out['state']={'ui_page':v.get('ui_page'),'avatar_visible':v['avatar_display']['visible'],'pair_ready':v['character_pair']['state']=='READY','runtime_fault_count':v['runtime_faults']['count'],'listening_enabled':h['enabled'],'microphone_open':h['microphone_open'],'handsfree_state':h['state'],'playing':bool(v.get('playing')),'pending_job':bool(v.get('pending_job')),'automatic_following':pan['automatic_following'],'axis_readback':{k:rb.get(k) for k in ('flags','lease_left_ms','width_us','active','armed')},'speaker':{k:speaker.get(k) for k in ('ready','identity_match_threshold','identity_ambiguity_margin','speaker_calibrated','single_cpu_worker','conversation_address','submitted','complete','evidence_errors')}}
    assert out['state']['runtime_fault_count']==0 and not out['state']['automatic_following'] and out['state']['speaker']['identity_match_threshold']==.35
assert out['camera_owner_unchanged'] and out['source_unchanged']
out['board_mono_ms']=int(time.monotonic()*1000);print(json.dumps(out))
