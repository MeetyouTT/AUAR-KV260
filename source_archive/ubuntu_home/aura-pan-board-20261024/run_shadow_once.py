"""Run exactly one bounded live shadow and compare native/UI health around it."""
import hashlib,json,os,subprocess,time,urllib.request
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
boot=Path('/proc/sys/kernel/random/boot_id').read_text().strip()
before=brief();u=get(8783,'/api/state');m=u.get('manual_pan',{});r=m.get('readback',{})
assert u['phase']=='IDLE' and not u.get('playing') and u.get('audio_output_state')=='IDLE_READY'
assert m.get('state') not in ('MOVING','STOPPING','CONNECTING') and not m.get('automatic_following')
folder=SH/'runs'/('live-'+str(time.monotonic_ns()));out=folder/'shadow.jsonl'
meta=json.loads((Path('/home/root/aura-native-live-20261024/ops/be72669aa53de735')/'meta.json').read_text())
follow=SH/'follow.py';alias=SH/'shadow_follow.py'
assert alias.is_file() and hashlib.sha256(alias.read_bytes()).hexdigest()==hashlib.sha256(follow.read_bytes()).hexdigest()
cfg=json.loads(Path(meta['candidate_config']).read_text());checkpoint=json.loads(Path(cfg['native_execution']['checkpoint_output']).read_text())
checkpoint_source_pid=checkpoint.get('seed',{}).get('source_pid')
assert isinstance(checkpoint_source_pid,int) and checkpoint.get('seed',{}).get('boot_id')!=boot
app_root=str(Path(meta['candidate_root'])/'aura')
cmd=['/usr/bin/python3','-B',str(SH/'run_shadow.py'),'--app-root',app_root,'--config',str(SH/'config.json'),'--duration','10','--output',str(out)]
env=dict(os.environ);env['PYTHONPATH']=app_root
p=subprocess.run(cmd,env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,timeout=30)
if p.returncode:
 print(json.dumps({'shadow_child_exit':p.returncode,'stderr_tail':p.stderr[-800:],'stdout_tail':p.stdout[-400:]}))
 raise SystemExit(2)
summary=json.loads((folder/'shadow.jsonl.summary.json').read_text()) if (folder/'shadow.jsonl.summary.json').exists() else None
after=brief();u2=get(8783,'/api/state');m2=u2.get('manual_pan',{})
assert after['pid']==before['pid'] and after['frames']>before['frames'] and after['primary_overruns']==before['primary_overruns']
assert after['optional_overruns']==before['optional_overruns'] and after['gaps']==before['gaps']
assert after['identity_ready'] and after['worker_alive'] and not after['owner_fenced']
assert m2.get('state') not in ('MOVING','STOPPING','CONNECTING') and not m2.get('automatic_following')
assert summary and summary['physical_actuation'] is False and summary['register_writes']==0 and summary['elapsed_s']<=10.5
result={'exit_code':p.returncode,'shadow':summary,'camera_pid_same':True,'camera_frames_delta':after['frames']-before['frames'],
 'new_primary_overruns':after['primary_overruns']-before['primary_overruns'],
 'new_optional_overruns':{k:after['optional_overruns'][k]-before['optional_overruns'][k] for k in before['optional_overruns']},
 'new_gaps':after['gaps']-before['gaps'],'current_boot':boot,'checkpoint_source_pid':checkpoint_source_pid,
 'manual_backend_state_before':m.get('state'),
 'shadow_import_alias_sha256':hashlib.sha256(alias.read_bytes()).hexdigest(),
 'raw_shadow_path':str(out),'raw_shadow_mode_0600':oct(out.stat().st_mode & 0o777)}
print(json.dumps(result,sort_keys=True))
