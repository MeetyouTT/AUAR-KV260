import hashlib,json,subprocess,time,urllib.request
from pathlib import Path
R=Path('/home/root/aura-pan-current-20261024/16a07283')
P=Path('/home/root/aura-native-live-20261024/ops/be72669aa53de735/pan-face-edge-v5/continuous-v10r14')
o=urllib.request.build_opener(urllib.request.ProxyHandler({}))
def manual():
 with o.open('http://127.0.0.1:8783/api/state',timeout=3) as f:return json.load(f)['manual_pan']
m=manual();assert m['state']=='READY' and not m['automatic_following']
assert m['readback']['flags']==0 and m['readback']['lease_left_ms']==0
manifest=json.loads((P/'deployment-manifest.json').read_text())
assert all(hashlib.sha256(Path(x['destination']).read_bytes()).hexdigest()==x['sha256'] for x in manifest['files'])
out=P/('readonly-input-'+str(time.monotonic_ns())+'.json')
code="import faulthandler,runpy,sys;faulthandler.dump_traceback_later(12);sys.path.insert(0,"+repr(str(P))+");runpy.run_path("+repr(str(P/'run_input_diagnostics.py'))+",run_name='__main__')"
args=['/usr/bin/python3','-B','-c',code,'--settings',str(R/'face-zone-settings.json'),'--output',str(out),'--duration','8']
try:
 job=subprocess.run(args,capture_output=True,text=True,timeout=18)
 result=dict(returncode=job.returncode,stderr=job.stderr[-3000:],diagnostics=json.loads(out.read_text()) if out.exists() and out.stat().st_size else None,output=str(out))
except subprocess.TimeoutExpired as exc:
 result=dict(status='READONLY_DIAGNOSTIC_TIMEOUT',stderr=(exc.stderr or b'').decode('utf-8','replace')[-3000:],output=str(out))
after=manual();assert after['readback']==m['readback'] and after['state']=='READY' and not after['automatic_following']
result.update(readback_unchanged=True,motor_commands_sent=0)
print(json.dumps(result))
