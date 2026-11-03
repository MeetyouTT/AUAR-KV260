"""Run exactly one bounded live shadow and compare native/UI health around it."""
import json,subprocess,time,urllib.request
from pathlib import Path
SH=Path('/home/root/aura-native-live-20261024/ops/be72669aa53de735/pan-follow-shadow-live')
def get(port,path):
 o=urllib.request.build_opener(urllib.request.ProxyHandler({}))
 with o.open('http://127.0.0.1:%d%s'%(port,path),timeout=3) as r:return json.load(r)
def brief():
 h=get(8790,'/health');s=h['dpu_schedule'];i=h['identity'];t=i['face_targets']
 return {'pid':h['pid'],'frames':h['detected_frames'],'primary_calls':s['primary_calls'],'primary_overruns':s['primary_period_overruns'],
  'optional_overruns':{k:s['optional'][k]['overruns'] for k in ('yunet','sface')},'optional_disabled':{k:s['optional'][k]['disabled'] for k in ('yunet','sface')},
  'gaps':t['freshness_metrics']['counters']['observed_gap_intervals'],'identity_ready':i['ready'],'worker_alive':t['worker_alive'],'owner_fenced':s['owner_fenced']}
s=json.loads((SH/'stage-state.json').read_text());assert s['phase']=='CAMERA_READY_WITH_MOTION_FEED'
before=brief();u=get(8783,'/api/state');m=u.get('manual_pan',{});r=m.get('readback',{})
assert u['phase']=='IDLE' and not u.get('playing') and u.get('audio_output_state')=='IDLE_READY'
assert r.get('flags')==0 and r.get('lease_left_ms')==0 and not r.get('active') and not r.get('armed') and not m.get('automatic_following')
folder=SH/'runs'/('live-'+str(time.monotonic_ns()));out=folder/'shadow.jsonl'
meta=json.loads((Path('/home/root/aura-native-live-20261024/ops/be72669aa53de735')/'meta.json').read_text())
cmd=['/usr/bin/python3','-B',str(SH/'run_shadow.py'),'--app-root',meta['candidate_root']+'/aura','--config',str(SH/'config.json'),'--duration','10','--output',str(out)]
p=subprocess.run(cmd,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,timeout=30)
assert p.returncode==0
summary=json.loads((folder/'shadow.jsonl.summary.json').read_text()) if (folder/'shadow.jsonl.summary.json').exists() else None
after=brief();u2=get(8783,'/api/state');m2=u2.get('manual_pan',{});r2=m2.get('readback',{})
assert after['pid']==before['pid'] and after['frames']>before['frames'] and after['primary_overruns']==before['primary_overruns']
assert after['optional_overruns']==before['optional_overruns'] and after['gaps']==before['gaps']
assert after['identity_ready'] and after['worker_alive'] and not after['owner_fenced']
assert r2.get('flags')==0 and r2.get('lease_left_ms')==0 and not r2.get('active') and not r2.get('armed')
assert summary and summary['physical_actuation'] is False and summary['register_writes']==0 and summary['elapsed_s']<=10.5
result={'exit_code':p.returncode,'shadow':summary,'camera_pid_same':True,'camera_frames_delta':after['frames']-before['frames'],
 'new_primary_overruns':after['primary_overruns']-before['primary_overruns'],
 'new_optional_overruns':{k:after['optional_overruns'][k]-before['optional_overruns'][k] for k in before['optional_overruns']},
 'new_gaps':after['gaps']-before['gaps'],'manual_output_stopped':True,'raw_shadow_path':str(out),'raw_shadow_mode_0600':oct(out.stat().st_mode & 0o777)}
print(json.dumps(result,sort_keys=True))
