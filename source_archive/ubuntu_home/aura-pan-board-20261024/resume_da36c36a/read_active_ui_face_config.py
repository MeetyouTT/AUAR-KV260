import json,re,subprocess,urllib.request
from pathlib import Path
props=subprocess.check_output(['systemctl','show','aura-avatar-ui.service','-p','MainPID','-p','ExecStart','-p','NRestarts'],text=True)
match=re.search(r'--config (/[^ ;]+)',props);assert match
cfg=json.loads(Path(match.group(1)).read_text());runtime=Path(cfg['runtime'])/'aura'
face=json.loads((runtime/'config/pan_face.local.json').read_text())
with urllib.request.build_opener(urllib.request.ProxyHandler({})).open('http://127.0.0.1:8783/api/state',timeout=3) as f:s=json.load(f)
m=s['manual_pan'];r=m.get('readback') or {};v=s['ui_runtime'].get('preview_metrics') or {}
print(json.dumps({'gui_pid':dict(x.split('=',1) for x in props.splitlines() if '=' in x).get('MainPID'),
 'ui_page':s.get('ui_page'),'preview_frame':(v.get('frame_reference') or {}).get('frame_id'),'preview_active':v.get('sink_active'),
 'manual_state':m['state'],'automatic_following':m['automatic_following'],'readback':{k:r.get(k) for k in ('flags','width_us','lease_left_ms','epoch','ack_seq')},
 'face_config_path':str(runtime/'config/pan_face.local.json'),'face_mode':face.get('mode'),
 'face_release':Path(face.get('release_root','')).name,'follow_duration_s':face.get('duration_s'),
 'zone_recenter_enabled':json.loads(Path('/home/root/aura-pan-current-20261024/da36c36a/face-zone-settings.json').read_text()).get('recenter_on_edge'),
 'recenter_target':.5,'execstart_pins':len(cfg.get('component_sha256',{}))}))
