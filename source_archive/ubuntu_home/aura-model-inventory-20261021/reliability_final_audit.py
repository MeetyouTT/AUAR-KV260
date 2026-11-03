import base64,gzip,hashlib,json,subprocess,urllib.request
from pathlib import Path
root=Path('/home/root/aura-vision-reliability-20261023/60d811453ecbfbd5')
d=json.loads((root/'report.json').read_text());assert d['complete'] and d['passed'] and d['accepted']
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
release=Path(d['release']);assert sha('/etc/systemd/system/aura-camera-ui.service')==d['unit_sha256']
assert sha(d['database'])==d['database_sha256'] and sha(d['identity_config'])==d['identity_config_sha256']
files={}
for name,digest in d['candidate_pins'].items():
 path=(Path(d['gui_runtime']) if name=='board/identity/spoken_query.py' else release)/'aura'/name
 assert sha(path)==digest
 raw=path.read_bytes();files[('gui/aura/' if name=='board/identity/spoken_query.py' else 'camera/aura/')+name]={'sha256':digest,'base64':base64.b64encode(raw).decode()}
for name in ('runtime_entry.py','gil_camera_launcher.py','restore_previous.py'):
 p=release/name;files['camera/'+name]={'sha256':sha(p),'base64':base64.b64encode(p.read_bytes()).decode()}
op=urllib.request.build_opener(urllib.request.ProxyHandler({}))
with op.open('http://127.0.0.1:8790/health',timeout=3) as r:h=json.load(r)
with op.open('http://127.0.0.1:8783/api/state',timeout=3) as r:u=json.load(r)
i=h['identity'];f=i['face_targets'];s=h['dpu_schedule']
assert h['pid']==d['camera_pid'] and i['ready'] and i['backend']=='DPU_SFACE_INT8'
assert i['feature_inference']['ready'] and f['worker_alive'] and not f['fault_latched']
assert not s['owner_fenced'] and s['diagnostic_failures']==0
assert all(not s['optional'][k]['overruns'] and not s['optional'][k]['disabled'] for k in ('yunet','sface'))
assert s['primary_period_overruns']==d['observation']['initial_primary_period_overruns']
assert f['freshness_metrics']['counters']['observed_gap_intervals']==0
session=json.loads((Path(d['session'])/'session.json').read_text())
assert not session['guard_armed'] and session['accepted_target']=='candidate'
guard=session['guard']
units=[guard+'.timer','aura-vision-reliability-60d811453ecbfbd5.service']
states={n:subprocess.check_output(['systemctl','show',n,'-p','ActiveState','--value']).decode().strip() for n in units}
assert all(v=='inactive' for v in states.values())
checked=subprocess.run(['/usr/bin/python3','-B',d['rollback'],'--check'],stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=12,text=True)
assert checked.returncode==0,checked.stderr[-200:]
old_db=Path('/home/root/.local/share/aura/identities.sqlite3');old_sha=sha(old_db)
assert old_sha=='e0d2113eb51171079978b1e63eb4263d5fb13235fec1839f7be778dab1520aa1'
payload={'boot':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),'accepted':True,
 'release':d['release'],'gui_runtime':d['gui_runtime'],'unit_sha256':d['unit_sha256'],
 'camera_pid':d['camera_pid'],'gui_pid':d['gui_pid'],'xserver_pid':d['xserver_pid'],
 'board_isolated':d['board_isolated'],'observation':d['observation'],
 'identity_config_sha256':d['identity_config_sha256'],'database_sha256':d['database_sha256'],
 'old_windows_database_sha256':old_sha,'original_int8_database_preserved':True,
 'candidate_pins':d['candidate_pins'],'rollback':d['rollback'],'rollback_check':json.loads(checked.stdout),
 'guard_and_controller':states,'current':{'yolo_hz':h['detection_hz'],'capture_hz':h['capture_hz'],
 'identity_backend':i['backend'],'feature_status':i['feature_status'],'feature_inference':i['feature_inference'],
 'face_backend':f['backend'],'worker_alive':f['worker_alive'],'worker_faults':f['worker_faults'],
 'fallback':f.get('inference'),'gaps':f['freshness_metrics']['counters']['observed_gap_intervals'],
 'face_source_age_ms':f['source_age_ms'],'optional':s['optional'],'owner_fenced':s['owner_fenced'],
 'diagnostic_failures':s['diagnostic_failures'],'primary_period_overruns':s['primary_period_overruns']},
 'ui':{k:u.get(k) for k in ('phase','playing','paused','audio_output_state')},
 'source_files':files,'report_sha256':sha(root/'report.json')}
raw=json.dumps(payload,separators=(',',':')).encode()
print(json.dumps({'passed':True,'source_files':len(files),'gzip_base64':base64.b64encode(gzip.compress(raw,mtime=0)).decode()}))
