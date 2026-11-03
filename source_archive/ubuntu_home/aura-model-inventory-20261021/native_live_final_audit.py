import hashlib,json,os,subprocess,time,urllib.request
from pathlib import Path
root=Path('/home/root/aura-native-live-20261024/ops/be72669aa53de735')
meta=json.loads((root/'meta.json').read_text());state=json.loads((root/'state.json').read_text())
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()=='a69299ef-17d0-446f-a0df-56c0a08cd2fb'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
for path,pin in meta['protected'].items():assert sha(path)==pin,path
for name,pin in meta['source_pins'].items():assert sha(root/name)==pin,name
op=urllib.request.build_opener(urllib.request.ProxyHandler({}))
def get(port,path):
 with op.open('http://127.0.0.1:'+str(port)+path,timeout=4) as r:return json.load(r)
h=get(8790,'/health');s=h['dpu_schedule'];face=h['identity']['face_targets'];feature=h['identity']['feature_inference']
g=get(8783,'/api/state')
units={}
for u in ['aura-camera-ui.service','aura-avatar-ui.service','xserver-nodm.service']:
 text=subprocess.check_output(['systemctl','show',u,'-p','ActiveState','-p','MainPID','-p','NRestarts','-p','Restart','-p','KillMode','-p','SendSIGKILL'],text=True)
 units[u]=dict(line.split('=',1) for line in text.splitlines() if '=' in line)
config=json.loads(Path(meta['candidate_config']).read_text());identity_path=Path(config['identity']['config']);identity=json.loads(identity_path.read_text())
assert sha(identity_path)=='398ece6a4d5d81076c9a4f9f40a43e97cedd469e0b47e3a835e589a2255ca6e3'
assert sha(identity['database'])=='ee22b97dbaa6f29f5b76c18565acc4f597cd61c6090f1946b993d2a29ab8101a'
tracing=Path('/sys/kernel/tracing')
probes=[line.split()[0] for line in (tracing/'uprobe_events').read_text().splitlines() if any(n in line for n in ['aura_optional_','aura_iso_','aura_vart_'])]
instances=[p.name for p in (tracing/'instances').iterdir() if p.name.startswith(('aura_optional_','aura_iso_','aura_vart_'))]
cu=Path('/sys/devices/platform/axi/axi:zyxclmm_drm/CU.3.auto/stat')
a=[int(v) for v in cu.read_text().split()];before=h['detected_frames'];time.sleep(1.5);later=get(8790,'/health');b=[int(v) for v in cu.read_text().split()]
stopped=a[0]==b[0] and later['pid']==h['pid'] and later['detected_frames']-before>=5
report={'read_only':True,'boot':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),'mono_ns':time.monotonic_ns(),
 'state_phase':state['phase'],'window':state.get('last_window'),'camera':{k:h[k] for k in ['pid','detected_frames','capture_frames','detection_hz','capture_hz','camera_error','detector_error','observation_age_ms']},
 'primary_calls':s['primary_calls'],'primary_period_overruns':s['primary_period_overruns'],'optional':s['optional'],
 'feature_inference':feature,'face':{k:face.get(k) for k in ['ready','backend','worker_alive','error','source_age_ms','processed']},
 'freshness_counters':face['freshness_metrics']['counters'],'pipeline_metrics':h['pipeline_metrics'],
 'owner_fenced':s['owner_fenced'],'native_abi':s.get('native_abi'),'handoff':s['protection_handoff'],
 'services':units,'gui':{k:g.get(k) for k in ['phase','audio_output_state','ui_page','playing','paused']},
 'identity_config_sha256':sha(identity_path),'database_sha256':sha(identity['database']),
 'candidate_root':meta['candidate_root'],'protected_files_verified':len(meta['protected']),
 'own_uprobes':probes,'own_instances':instances,'cu_statistics_stopped':stopped,
 'thread_nice':{p.name:os.getpriority(os.PRIO_PROCESS,int(p.name)) for p in (Path('/proc')/str(h['pid'])/'task').iterdir()}}
print(json.dumps(report))
