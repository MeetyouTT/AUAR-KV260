"""Restore pause after a desktop turn interruption; do not launch another test."""
from pathlib import Path
import hashlib,json,sys,time
HERE=Path(__file__).resolve().parents[1];PROJECT=HERE.parents[3]
sys.path.insert(0,str(PROJECT/'deliverables/2026-10-18_board_dialogue'))
from board_ssh import ssh

def main():
 folder=HERE/'evidence/live_trial_1793534402189129700'
 post=json.loads((HERE/'evidence/single_projection_post_baseline_1793533717316425200.json').read_bytes())['result']
 spec=json.loads((HERE/'package/single_projection/candidate_spec.json').read_bytes())
 source=(HERE/'package/single_projection/camera_binding_runtime.py').read_text('utf-8')+'\n'
 source+=(HERE/'remote/common.py').read_text('utf-8').replace('8ff79452570385921e06c098b5d42c2ea1ef5dfb84d81dfa7f53a9295373d0e8',spec['source_manifest_sha256'])+'\n'
 source+='STARTUP_SHA='+repr(spec['startup_sha256'])+'\nEXPECTED_OWNERS='+repr(post['after']['owners'])+'\n'+REMOTE
 result=json.loads(ssh('python3 -B -',source,timeout=65))
 raw=(json.dumps(dict(utc=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),source_sha256=hashlib.sha256(source.encode()).hexdigest(),result=result),indent=2)+'\n').encode()
 path=folder/('INTERRUPTION_RECOVERY_'+str(time.time_ns())+'.json')
 with path.open('xb') as f:f.write(raw)
 latest=dict(status=result['status'],recovery=str(path),ready=str(folder/'READY.json'),evidence=str(folder/'metadata.jsonl'))
 (HERE/'LIVE_LATEST.json').write_text(json.dumps(latest,indent=2)+'\n',encoding='utf-8')
 print(json.dumps(dict(evidence=str(path),sha256=hashlib.sha256(raw).hexdigest(),result=result),ensure_ascii=False))

REMOTE=r'''
def current_guard():
 assert os.geteuid()==0 and os.uname().machine=='aarch64'
 assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==BOOT
 assert digest(BUSINESS/'startup/config.json')==STARTUP_SHA
def assert_safe(value):
 s=safe_state(value);r=s['readback']
 assert s['following'] is False and s['pan_state']=='READY'
 assert r['flags']==0 and r['lease_left_ms']==0 and r['active'] is False and r['armed'] is False
 return s
before,v,h=preflight()
initial=safe_state(v)
def tag(value):
 return hashlib.sha256(value.encode()).hexdigest() if isinstance(value,str) and value else None
task=v.get('local_transcription',{});ack=v.get('board_business',{}).get('dialogue',{}).get('last_playback_ack') or {}
metadata=dict(request_token=tag(task.get('request_id')),ack_request_token=tag(ack.get('request_id')),
              ack_committed=ack.get('committed') is True,
              transcription_state=task.get('state') if task.get('state') in ('IDLE','DISABLED','ANSWERED','GENERATING','TRANSCRIBING','PLAYING','CANCELLED') else 'OTHER')
deadline=time.monotonic()+30
while (v.get('playing') is True or v.get('local_transcription',{}).get('state') in ('TRANSCRIBING','GENERATING','PLAYING')) and time.monotonic()<deadline:
 time.sleep(.2);v=get_json(8783,'/api/state');assert_safe(v)
assert v.get('playing') is False and v.get('local_transcription',{}).get('state') not in ('TRANSCRIBING','GENERATING','PLAYING'),'current_answer_not_finished'
command_sent=False
if v.get('handsfree_dialogue',{}).get('enabled') is True:
 c=http.client.HTTPConnection('127.0.0.1',8783,timeout=5)
 try:
  c.request('POST','/api/command',body=json.dumps(dict(type='conversation_toggle')),headers={'Content-Type':'application/json','Origin':'http://127.0.0.1:8783'})
  r=c.getresponse();data=r.read(100001);assert r.status==200 and len(data)<=100000 and json.loads(data).get('ok') is True
  command_sent=True
 finally:c.close()
deadline=time.monotonic()+10
while time.monotonic()<deadline:
 v=get_json(8783,'/api/state');s=assert_safe(v)
 if s['listening_enabled'] is False and s['listening_state']=='PAUSED' and s['microphone_open'] is False and s['playing'] is False:break
 time.sleep(.2)
else:raise RuntimeError('interrupted_test_pause_not_confirmed')
after,_,_=preflight()
assert document('/home/root/.local/share/aura-board-business/listening_preference.json')=={'version':1,'enabled':False}
print(json.dumps(dict(status='INTERRUPTED_WINDOW_FINAL_PAUSED',before=before,initial_metadata=metadata,after=after,
                     normal_pause_toggle_sent=command_sent,new_trial_started=False,original_trial_completion_unknown=True)))
'''
if __name__=='__main__':main()
