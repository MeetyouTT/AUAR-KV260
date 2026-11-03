import hashlib,json,subprocess,urllib.request
from pathlib import Path
N=Path('/home/root/aura-pan-current-20261024/463c9307/gui-face-edge-v5');A=N/'runtime/aura'
F=Path('/home/root/aura-native-live-20261024/ops/be72669aa53de735/pan-face-edge-v5');R=F/'continuous-v5'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def get(port,path):
 o=urllib.request.build_opener(urllib.request.ProxyHandler({}))
 with o.open('http://127.0.0.1:%d%s'%(port,path),timeout=3) as r:return json.load(r)
c=json.loads((N/'startup/config.json').read_text());assert all(sha(A/n)==h for n,h in c['component_sha256'].items())
face=json.loads((A/'config/pan_face.local.json').read_text());m=R/'deployment-manifest.json'
assert face['release_root']==str(R) and sha(m)==face['manifest_sha256']=='e3f0cb1c029a778dad5130cb09a40929a8bbb00835ea4ebd4d015627cdea16bc'
assert all(sha(x['destination'])==x['sha256'] for x in json.loads(m.read_text())['files'])
source=F/'face-source-v9/deployment-manifest.json';assert sha(source)=='875f5c4fb3cde6c827063716eed52162a38caeb743b018f7e308a1a82da0055d'
assert all(sha(p)==h for p,h in json.loads(source.read_text())['pins'].items())
pids=[]
for p in Path('/proc').glob('[0-9]*/cmdline'):
 try:
  if str(R/'run_face_motion.py').encode() in p.read_bytes().split(b'\0'):pids.append(int(p.parent.name))
 except OSError:pass
assert len(pids)==1,pids
assert str(R/'libvsrv_batch.so') in (Path('/proc')/str(pids[0])/'maps').read_text()
u=get(8783,'/api/state');h=get(8790,'/health');s=h['dpu_schedule'];manual=u['manual_pan'];report=json.loads(Path(manual['face_follow']['report']).read_text())
assert manual['automatic_following'] and not report['result']['fatal']
print(json.dumps(dict(status='CONTINUOUS_V5_CURRENT_RUNTIME_VERIFIED',boot=report['boot_id'],pins=len(c['component_sha256']),
 camera_pid=h['pid'],gui_pid=int(subprocess.check_output(['systemctl','show','aura-avatar-ui.service','-p','MainPID','--value'],text=True)),
 consumer_pid=pids[0],loaded_library_sha256=sha(R/'libvsrv_batch.so'),consumer_manifest_sha256=sha(m),source_manifest_sha256=sha(source),
 identity_ready=h['identity']['ready'],owner_fenced=s['owner_fenced'],primary=s['primary_period_overruns'],
 optional={k:s['optional'][k]['overruns'] for k in ('yunet','sface')},preview=u['ui_runtime'].get('preview_metrics'),
 manual=manual,trial=report)))
