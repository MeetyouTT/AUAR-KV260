import hashlib,json,urllib.request
from pathlib import Path
R=Path('/home/root/aura-pan-current-20261024/16a07283');o=urllib.request.build_opener(urllib.request.ProxyHandler({}))
def get(port,path):
 with o.open('http://127.0.0.1:%d%s'%(port,path),timeout=3) as r:return json.load(r)
s=json.loads((R/'state.json').read_text());u=get(8783,'/api/state');m=u['manual_pan'];h=get(8790,'/health')
report_path=(m.get('face_follow') or {}).get('report');report=None
if report_path:
 path=Path(report_path);path.resolve(strict=True).relative_to(Path(s['physical_consumer_root'])/'runs');report=json.loads(path.read_text())
 assert report['boot_id']==s['boot'] and report['consumer_manifest_sha256']==s['physical_consumer_sha256']
 if not m['automatic_following']:
  assert m['state']=='READY' and m['readback']['flags']==0 and m['readback']['lease_left_ms']==0 and m['left_sign']==-1
  s.update(phase='FACE_CENTER_TEST_STOPPED_FEEDBACK_PENDING',center_test_report=str(path),
   center_test_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),current_last_command_us=m['readback']['width_us'],automatic_following=False)
  (R/'state.json').write_text(json.dumps(s,ensure_ascii=False,indent=2)+'\n')
trace_path=R/'face-zone-display-status.json'
print(json.dumps({'status':'RUNNING' if m['automatic_following'] else s['phase'],'manual':m,'report':report,
 'zone_display':json.loads(trace_path.read_text()) if trace_path.exists() else None,'camera_pid':h['pid'],'identity_ready':h['identity']['ready'],
 'owner_fenced':h['dpu_schedule']['owner_fenced'],'primary_overruns':h['dpu_schedule']['primary_period_overruns'],
 'optional_overruns':{k:h['dpu_schedule']['optional'][k]['overruns'] for k in ('yunet','sface')},'motor_commands_sent_by_probe':0}))
