import hashlib,json,os,re,subprocess,urllib.request
from pathlib import Path
ROOT=Path('/home/root/aura-native-live-20261024/ops/be72669aa53de735/pan-face-edge-v5/continuous-v13r1');R=Path('/home/root/aura-pan-current-20261024/da36c36a')
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
op=urllib.request.build_opener(urllib.request.ProxyHandler({}))
def get(port,path):
 with op.open('http://127.0.0.1:%d%s'%(port,path),timeout=3) as f:return json.load(f)
u=get(8783,'/api/state');h=get(8790,'/health');m=u['manual_pan'];p=Path(m['face_follow']['report']);p.relative_to(ROOT/'runs')
d=json.loads(p.read_text());assert d['consumer_manifest_sha256']=='ec300d3a8bb7a4828000846cb60ede2352ae6e86c44d5786eb50b3bf399a8e9a' and d['status']=='CONTINUOUS_FACE_ZONE_RUNNING'
raw=subprocess.check_output(['systemctl','show','aura-avatar-ui.service','-p','ExecStart','--value'],text=True);sc=Path(re.search(r'--config (/[^ ;]+)',raw).group(1));startup=json.loads(sc.read_text());app=Path(startup['runtime'])/'aura'
assert all(sha(app/n)==v for n,v in startup['component_sha256'].items())
cfg=json.loads(Path(json.loads((app/'config/pan_manual.local.json').read_text())['face_follow_config']).read_text());assert cfg['duration_s']==0 and cfg['release_root']==str(ROOT)
manifest=json.loads((ROOT/'deployment-manifest.json').read_text());assert all(sha(x['destination'])==x['sha256'] for x in manifest['files'])
r=d['result'];state=json.loads((R/'state.json').read_text());gui=int(subprocess.check_output(['systemctl','show','aura-avatar-ui.service','-p','MainPID','--value'],text=True))
state.update(phase='V13_SINGLE_PASS_CONTINUOUS_MONITOR',automatic_following=m['automatic_following'],current_gui_pid=gui,current_camera_pid=h['pid'],physical_consumer_root=str(ROOT),physical_consumer_sha256=d['consumer_manifest_sha256'],latest_report=str(p),last_report_mono_ms=r['heartbeat_mono_ms'])
t=R/('state.json.v13-final-'+str(os.getpid()));t.write_text(json.dumps(state,indent=2)+'\n');os.replace(t,R/'state.json')
preview=u.get('ui_runtime',{}).get('preview_metrics') or {}
print(json.dumps(dict(status=state['phase'],boot_id=d['boot_id'],controller='continuous-v13r1',controller_manifest_sha256=d['consumer_manifest_sha256'],control_files=len(manifest['files']),gui_pins=len(startup['component_sha256']),gui_pid=gui,camera_pid=h['pid'],automatic_following=m['automatic_following'],manual_state=m['state'],duration_s=0,report=str(p),result=r,control_parameters=d['control_parameters'],input_summary=d['input_summary'],primary_overruns=h['dpu_schedule']['primary_period_overruns'],optional_overruns={k:v['overruns'] for k,v in h['dpu_schedule']['optional'].items()},preview_sink_active=preview.get('sink_active'),preview_frame=preview.get('frame_reference'),physical_smoothness_verified=False,hardware_commands_sent_by_audit=0,state_metadata_written=True),ensure_ascii=False))
