"""Read-only current native counters and shadow route state after boot."""
import json,re,subprocess,urllib.request
from pathlib import Path
def get(port,path):
 o=urllib.request.build_opener(urllib.request.ProxyHandler({}))
 with o.open('http://127.0.0.1:%d%s'%(port,path),timeout=3) as r:return json.load(r)
def props(unit):
 x=subprocess.check_output(['systemctl','show',unit,'-p','MainPID','-p','ActiveState','-p','ExecStart'],text=True)
 return dict(a.split('=',1) for a in x.splitlines() if '=' in a)
h=get(8790,'/health');s=h['dpu_schedule'];i=h['identity'];face=i['face_targets'];u=props('aura-camera-ui.service')
feed=get(8790,'/v1/motion/observation');cp='/home/root/aura-native-live-20261024/candidates/native-r4-metrics-fix/board_camera_ui.proposed.json'
config=json.loads(Path(cp).read_text());checkpoint=Path(config['native_execution']['checkpoint_output'])
d=json.loads(checkpoint.read_text()) if checkpoint.exists() else {};seed=d.get('seed',{})
argv=u.get('ExecStart','');entry=re.findall(r'argv\[\]=[^;]*',argv)
print(json.dumps({'boot':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
 'camera_pid':h.get('pid'),'camera_unit_pid':u.get('MainPID'),'camera_active':u.get('ActiveState'),
 'active_entry_basename':Path(entry[0].split()[-1]).name if entry else None,
 'health':{'native_critical':s.get('native_critical'),'owner_fenced':s.get('owner_fenced'),
  'detected_frames':h.get('detected_frames'),'detection_hz':h.get('detection_hz'),
  'primary_calls':s.get('primary_calls'),'primary_overruns':s.get('primary_period_overruns'),
  'yunet_calls':s['optional']['yunet'].get('calls'),'yunet_overruns':s['optional']['yunet'].get('overruns'),
  'sface_calls':s['optional']['sface'].get('calls'),'sface_overruns':s['optional']['sface'].get('overruns'),
  'sface_completed':i['feature_inference'].get('completed'),'gaps':face['freshness_metrics']['counters'].get('observed_gap_intervals'),
  'identity_ready':i.get('ready'),'worker_alive':face.get('worker_alive')},
 'feed':{'state':feed.get('state'),'source_kind':feed.get('source_kind'),'source_age_ms':h.get('observation_age_ms'),
  'target_present':isinstance(feed.get('target'),dict)},
 'last_checkpoint_source_pid':seed.get('source_pid'),'last_checkpoint_boot':seed.get('boot_id'),
 'last_checkpoint_pending_results':sum(bool(x) for x in d.get('auxiliary',{}).get('pending_result_tokens',[]))},sort_keys=True))
