"""Read only the failing guard's static location and whitelisted state; no resume or playback."""
from pathlib import Path
import hashlib,json,sys,time
HERE=Path(__file__).resolve().parents[1];PROJECT=HERE.parents[3]
sys.path.insert(0,str(PROJECT/'deliverables/2026-10-18_board_dialogue'))
from board_ssh import ssh

def main():
 post=json.loads((HERE/'evidence/single_projection_post_baseline_1793533717316425200.json').read_bytes())['result']
 spec=json.loads((HERE/'package/single_projection/candidate_spec.json').read_bytes())
 source=(HERE/'package/single_projection/camera_binding_runtime.py').read_text('utf-8')+'\n'
 source+=(HERE/'remote/common.py').read_text('utf-8').replace('8ff79452570385921e06c098b5d42c2ea1ef5dfb84d81dfa7f53a9295373d0e8',spec['source_manifest_sha256'])+'\n'
 source+='STARTUP_SHA='+repr(spec['startup_sha256'])+'\nEXPECTED_OWNERS='+repr(post['after']['owners'])+'\n'+REMOTE
 result=json.loads(ssh('python3 -B -',source,timeout=20))
 path=HERE/'evidence'/('live_preflight_diagnosis_'+str(time.time_ns())+'.json')
 with path.open('x',encoding='utf-8') as f:json.dump(dict(source_sha256=hashlib.sha256(source.encode()).hexdigest(),result=result),f,indent=2);f.write('\n')
 print(json.dumps(dict(evidence=str(path),result=result),ensure_ascii=False))

REMOTE=r'''
import traceback
def current_guard():
 assert os.geteuid()==0 and os.uname().machine=='aarch64'
 assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==BOOT
 assert digest(BUSINESS/'startup/config.json')==STARTUP_SHA
def assert_safe(value):
 s=safe_state(value);r=s['readback']
 assert s['following'] is False and s['pan_state']=='READY'
 assert r['flags']==0 and r['lease_left_ms']==0 and r['active'] is False and r['armed'] is False
 return s
result={}
try:
 v=get_json(8783,'/api/state');h=get_json(8790,'/health')
 result.update(state=safe_state(v),avatar=numeric(v.get('avatar_display')),camera_pid=h.get('pid'),
               phase=v.get('phase') if v.get('phase') in ('IDLE','ACTION','THINKING','SPEAKING') else 'OTHER',
               camera_errors_present={k:bool(h.get(k)) for k in ('camera_error','detector_error','preview_error')})
 before,_,_=preflight();result.update(status='PREFLIGHT_PASS',proof=before)
except Exception as exc:
 result.update(status='PREFLIGHT_REFUSED',error_class=type(exc).__name__,
               frames=[dict(file=Path(r.filename).name,line=r.lineno,function=r.name) for r in traceback.extract_tb(exc.__traceback__)][-5:])
print(json.dumps(result))
'''
if __name__=='__main__':main()
