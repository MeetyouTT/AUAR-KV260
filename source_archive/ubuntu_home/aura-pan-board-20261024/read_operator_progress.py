"""Anonymous service/protection/recovery status, no face names or vectors."""
import json,subprocess,time,urllib.request
from pathlib import Path
R=Path('/home/root/aura-native-live-20261024/ops/be72669aa53de735/pan-face-edge-v5/native-operator-v1')
op=urllib.request.build_opener(urllib.request.ProxyHandler({}))
def get(port,path):
 with op.open('http://127.0.0.1:%d%s'%(port,path),timeout=3) as r:return json.load(r)
h=get(8790,'/health');s=h['dpu_schedule'];u=get(8783,'/api/state');feature=h['identity']
files=sorted(R.glob('recovery-audit-*.json'),key=lambda x:x.stat().st_mtime);a=json.loads(files[-1].read_text()) if files else {}
print(json.dumps({'pid':h['pid'],'primary':s['primary_period_overruns'],'primary_calls':s['primary_calls'],'owner_fenced':s['owner_fenced'],
 'detection_hz':h['detection_hz'],'identity_ready':feature['ready'],'identity_error':feature['error'],
 'optional':{k:{name:s['optional'][k].get(name) for name in ('calls','native_completed','overruns','disabled','recovery')} for k in ('yunet','sface')},
 'audit_status':a.get('status'),'audit_error':a.get('error'),'audit_path':str(files[-1]) if files else None,
 'operator':{k:{n:a.get(k,{}).get(n) for n in ('status','guard_refusals')} for k in ('sface','yunet')},'health_probes':a.get('health_probes'),
 'preview':u['ui_runtime'].get('preview_metrics'),'manual':{k:u['manual_pan'].get(k) for k in ('state','automatic_following','readback')},
 'handoff':s.get('protection_handoff'),'boot':Path('/proc/sys/kernel/random/boot_id').read_text().strip()},sort_keys=True))
