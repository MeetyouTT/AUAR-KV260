"""After the observed full ACK, restore the original paused choice through the original UI command."""
from pathlib import Path
import hashlib,json,sys,time

HERE=Path(__file__).resolve().parents[1];PROJECT=HERE.parents[3]
sys.path.insert(0,str(PROJECT/'deliverables/2026-10-18_board_dialogue'))
from board_ssh import ssh


def main():
 latest=json.loads((HERE/'LIVE_LATEST.json').read_bytes());result_path=Path(latest['result'])
 result=json.loads(result_path.read_bytes())
 complete=next(r for r in result['terminal_events'] if r.get('status')=='ONE_NEW_TURN_COMPLETE')
 target=complete['request_token'];assert len(target)==64
 post=json.loads((HERE/'evidence/single_projection_post_baseline_1793533717316425200.json').read_bytes())['result']
 pkg=HERE/'package/single_projection';spec=json.loads((pkg/'candidate_spec.json').read_bytes())
 common=(HERE/'remote/common.py').read_text('utf-8').replace('8ff79452570385921e06c098b5d42c2ea1ef5dfb84d81dfa7f53a9295373d0e8',spec['source_manifest_sha256'])
 source=(pkg/'camera_binding_runtime.py').read_text('utf-8')+'\n'+common+'\n'
 source+='STARTUP_SHA='+repr(spec['startup_sha256'])+'\nEXPECTED_OWNERS='+repr(post['after']['owners'])+'\nTARGET='+repr(target)+'\n'+REMOTE
 receipt=json.loads(ssh('python3 -B -',source,timeout=35))
 path=result_path.parent/'FINAL_PAUSED.json';raw=(json.dumps(dict(source_sha256=hashlib.sha256(source.encode()).hexdigest(),result=receipt),indent=2)+'\n').encode()
 with path.open('xb') as f:f.write(raw)
 (HERE/'LIVE_LATEST.json').write_text(json.dumps(dict(status='ONE_TURN_COMPLETE_FINAL_PAUSED',result=str(result_path),final_paused=str(path),evidence=result['evidence']),indent=2)+'\n',encoding='utf-8')
 print(json.dumps(dict(status='ONE_TURN_COMPLETE_FINAL_PAUSED',final_paused=str(path),result=receipt),ensure_ascii=False))


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
ack=v.get('board_business',{}).get('dialogue',{}).get('last_playback_ack') or {}
token=ack.get('request_id')
latest_ack_matches_target=(ack.get('committed') is True and isinstance(token,str) and hashlib.sha256(token.encode()).hexdigest()==TARGET)
# The closed observer already sealed the target's matching full ACK. A later
# ambient turn may replace the last-ACK slot; it must not prevent test cleanup.
wait_end=time.monotonic()+20
while v.get('playing') is True and time.monotonic()<wait_end:
 time.sleep(.1);v=get_json(8783,'/api/state')
assert v.get('playing') is False,'wait_for_current_playback_before_pause'
phase_before_pause=v.get('phase')
was_enabled=v.get('handsfree_dialogue',{}).get('enabled');assert type(was_enabled) is bool
if was_enabled:
 c=http.client.HTTPConnection('127.0.0.1',8783,timeout=5)
 try:
  c.request('POST','/api/command',body=json.dumps(dict(type='conversation_toggle')),headers={'Content-Type':'application/json','Origin':'http://127.0.0.1:8783'})
  r=c.getresponse();raw=r.read(100001);assert r.status==200 and len(raw)<=100000 and json.loads(raw).get('ok') is True
 finally:c.close()
end=time.monotonic()+15
while time.monotonic()<end:
 v=get_json(8783,'/api/state');s=assert_safe(v)
 if s['listening_enabled'] is False and s['listening_state']=='PAUSED' and s['microphone_open'] is False and s['playing'] is False:break
 time.sleep(.2)
else:raise RuntimeError('normal_pause_not_confirmed')
after,_,_=preflight()
assert document('/home/root/.local/share/aura-board-business/listening_preference.json')=={'version':1,'enabled':False}
print(json.dumps(dict(status='FINAL_PAUSED',completed_request_token=TARGET,target_matching_full_ack_sealed_by_observer=True,
                     latest_ack_still_matches_target=latest_ack_matches_target,
                     prior_enabled=was_enabled,before=before,after=after,normal_toggle_sent=was_enabled,
                     completed_target_generation_or_playback_interrupted=False,
                     phase_before_pause=phase_before_pause)))
'''


if __name__=='__main__':main()
