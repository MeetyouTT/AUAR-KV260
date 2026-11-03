"""GET-only reconciliation; never repeat the prior pause request."""
import hashlib
import http.client
import json
from pathlib import Path
import subprocess

out={'schema':'aura-deferred-voice-pause-readonly-reconciliation-1','control_writes':0}
p=Path('/home/root/aura-board-business-20261030/production-5259eab11e42af13/startup/config.json');cfg=json.loads(p.read_bytes());aura=Path(cfg['runtime'])/'aura';out['startup_sha256']=hashlib.sha256(p.read_bytes()).hexdigest();out['boot_id']=Path('/proc/sys/kernel/random/boot_id').read_text().strip()
out['pause_intent_exists']=Path('/home/root/aura-5090-recovery-20261102-a6d4a069/voice-per-utterance-20261103T050551Z-stop/defer-listening-intent.json').is_file()
out['chosen_source_matches']={}
for name in ('board/runtime/board_speaker_business.py','board/runtime/board_dialogue.py','tools/native_yuki.py','tools/libaura_yuki.so'):
    f=aura/name;out['chosen_source_matches'][name]={'declared':name in cfg['component_sha256'],'exists':f.is_file(),'matches':f.is_file() and hashlib.sha256(f.read_bytes()).hexdigest()==cfg['component_sha256'].get(name)}
r=subprocess.run(['systemctl','show','aura-avatar-ui.service','--property=MainPID,ActiveState,SubState,Job,Restart,KillMode,SendSIGKILL,TimeoutStopUSec'],capture_output=True,text=True,timeout=4);out['GUI_unit']=dict(x.split('=',1) for x in r.stdout.splitlines() if '=' in x)
out['owners']=[]
for pid in (937589,937618,362659):
    q=Path('/proc')/str(pid);row={'pid':pid,'exists':q.exists()}
    if q.exists():row.update(birth_ticks=q.joinpath('stat').read_text().rsplit(')',1)[1].split()[19],command_sha256=hashlib.sha256(q.joinpath('cmdline').read_bytes()).hexdigest())
    out['owners'].append(row)
c=http.client.HTTPConnection('127.0.0.1',8783,timeout=3)
try:c.request('GET','/api/state');r=c.getresponse();assert r.status==200;v=json.loads(r.read(2097152))
finally:c.close()
h=v.get('handsfree_dialogue') or {};s=(v.get('board_business') or {}).get('speaker') or {};pan=v.get('manual_pan') or {};rb=pan.get('readback') or {}
out.update(state={'ui_page':v.get('ui_page'),'avatar_visible':(v.get('avatar_display') or {}).get('visible'),'pair_ready':(v.get('character_pair') or {}).get('state')=='READY','listening_enabled':h.get('enabled'),'microphone_open':h.get('microphone_open'),'handsfree_state':h.get('state'),'playing':bool(v.get('playing')),'pending_job':bool(v.get('pending_job')),'runtime_fault_count':(v.get('runtime_faults') or {}).get('count'),'speaker_mode':(s.get('conversation_address') or {}).get('mode'),'speaker_threshold':s.get('identity_match_threshold'),'automatic_following':pan.get('automatic_following'),'axis_readback':{k:rb.get(k) for k in ('flags','lease_left_ms','width_us','active','armed')}},saved_listening_preference=json.loads(Path('/home/root/.local/share/aura-board-business/listening_preference.json').read_bytes()))
print(json.dumps(out))
