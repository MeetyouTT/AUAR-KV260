"""Run one <=10s shadow stream and preserve camera/GUI health evidence."""
import hashlib,json,os,subprocess,time,urllib.request
from pathlib import Path
OPS=Path('/home/root/aura-native-live-20261024/ops/be72669aa53de735');SH=OPS/'pan-follow-shadow-stream-v2'
def get(port,path):
 o=urllib.request.build_opener(urllib.request.ProxyHandler({}))
 with o.open('http://127.0.0.1:%d%s'%(port,path),timeout=3) as r:return json.load(r)
def brief():
 h=get(8790,'/health');s=h['dpu_schedule'];i=h['identity'];t=i['face_targets']
 return {'pid':h['pid'],'frames':h['detected_frames'],'primary_overruns':s['primary_period_overruns'],
  'optional_overruns':{k:s['optional'][k]['overruns'] for k in ('yunet','sface')},
  'gaps':t['freshness_metrics']['counters']['observed_gap_intervals'],'ready':t['worker_alive'],'fenced':s['owner_fenced']}
state=json.loads(Path('/home/root/aura-pan-current-20261024/463c9307/state.json').read_text());boot=Path('/proc/sys/kernel/random/boot_id').read_text().strip()
assert state['phase']=='CURRENT_BOOT_MANUAL_READY_OUTPUT_STOPPED' and state['boot']==boot
manifest=json.loads((SH/'deployment-manifest.json').read_text())
for f in manifest['files']:assert hashlib.sha256(Path(f['destination']).read_bytes()).hexdigest()==f['sha256']
before=brief();u=get(8783,'/api/state');m=u.get('manual_pan',{})
assert before['pid']==state['current_camera_pid'] and before['ready'] and not before['fenced']
assert u['phase']=='IDLE' and not u.get('playing') and u.get('audio_output_state')=='IDLE_READY'
assert m.get('state') not in ('MOVING','STOPPING','CONNECTING') and not m.get('automatic_following')
meta=json.loads((OPS/'meta.json').read_text());cfg=json.loads(Path(meta['candidate_config']).read_text());cp=Path(cfg['native_execution']['checkpoint_output'])
assert hashlib.sha256(cp.read_bytes()).hexdigest()==state['checkpoint_sha256']
out=SH/'runs'/('live-'+str(time.monotonic_ns()))/'shadow.jsonl'
cmd=['/usr/bin/python3','-B',str(SH/'run_shadow_stream.py'),'--app-root',meta['candidate_root']+'/aura','--config',str(SH/'config.json'),'--duration','10','--output',str(out)]
p=subprocess.run(cmd,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,timeout=30)
if p.returncode:
 print(json.dumps({'child_exit':p.returncode,'stderr_tail':p.stderr[-800:],'stdout_tail':p.stdout[-1000:]}));raise SystemExit(2)
summary=json.loads(Path(str(out)+'.summary.json').read_text());after=brief();u=get(8783,'/api/state')
assert after['pid']==before['pid'] and after['frames']>before['frames'] and after['ready'] and not after['fenced']
assert u['phase']=='IDLE' and not u.get('playing') and not u.get('manual_pan',{}).get('automatic_following')
assert summary['register_writes']==0 and summary['physical_actuation'] is False and summary['elapsed_s']<=10.5
result={'boot':boot,'camera_pid':after['pid'],'gui_pid':state['current_gui_pid'],'shadow':summary,'frames_delta':after['frames']-before['frames'],
 'primary_delta':after['primary_overruns']-before['primary_overruns'],'optional_delta':{k:after['optional_overruns'][k]-before['optional_overruns'][k] for k in before['optional_overruns']},
 'gaps_delta':after['gaps']-before['gaps'],'fresh_checkpoint_source_pid':state['stop_source_pid'],'checkpoint_sha256':state['checkpoint_sha256'],
 'manual_backend_state':u.get('manual_pan',{}).get('state'),'raw_mode':oct(out.stat().st_mode & 0o777),'output':str(out)}
print(json.dumps(result,sort_keys=True))
