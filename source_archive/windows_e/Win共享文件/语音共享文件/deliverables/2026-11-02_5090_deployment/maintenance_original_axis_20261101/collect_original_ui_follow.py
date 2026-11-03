import datetime,http.client,json,time
from pathlib import Path
samples=[]
for i in range(3):
 c=http.client.HTTPConnection('127.0.0.1',8783,timeout=3)
 try:
  c.request('GET','/api/state');response=c.getresponse();v=json.loads(response.read(2097153));assert response.status==200
 finally:c.close()
 p=v.get('manual_pan') or {};f=p.get('face_follow') or {};r={};report={}
 if f.get('report'):
  path=Path(f['report']);assert str(path.resolve()).startswith('/home/root/aura-pan-wide-20261028/control-10282601/runs/')
  assert path.is_file() and not path.is_symlink() and path.stat().st_size<2097152
  report=json.loads(path.read_text());r=report.get('result') or {}
 samples.append({'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'page':v.get('ui_page'),'following':p.get('automatic_following'),'pan_state':p.get('state'),'pulse_us':p.get('pulse_us'),'pan_error_present':bool(p.get('error')),'face_ui':{k:f.get(k) for k in ('state','phase','reason','commands_accepted','segments','report')},'original_report':{'status':report.get('status'),'error':report.get('error'),'result':{k:r.get(k) for k in ('state','reason','pulse_us','commands_accepted','segments','visual_center_completions','hardware_ramp_commits','stopped')},'input_summary':report.get('input_summary'),'telemetry':report.get('telemetry')},'runtime_fault_count':(v.get('runtime_faults') or {}).get('count')})
 if i<2:time.sleep(1.2)
print(json.dumps({'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'samples':samples,'commands_sent':False}))
