import hashlib,json,subprocess,urllib.request
from pathlib import Path
G=Path('/home/root/aura-pan-current-20261024/da36c36a/gui-reference-bound-v2');A=G/'runtime/aura'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
cfg=json.loads((G/'startup/config.json').read_text());face=json.loads((A/'config/pan_face.local.json').read_text())
raw=subprocess.check_output(['systemctl','show','aura-avatar-ui.service','-p','MainPID','-p','ExecStart'],text=True)
o=urllib.request.build_opener(urllib.request.ProxyHandler({}))
with o.open('http://127.0.0.1:8783/api/state',timeout=3) as f:u=json.load(f)
with o.open('http://127.0.0.1:8790/health',timeout=3) as f:h=json.load(f)
m=u['manual_pan'];r=m.get('readback') or {};print(json.dumps({'boot':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
 'camera_pid':h['pid'],'owner_fenced':h['dpu_schedule']['owner_fenced'],'GUI_source_start':raw,
 'startup_pins':len(cfg['component_sha256']),'startup_config_sha256':sha(G/'startup/config.json'),
 'face_config_sha256':sha(A/'config/pan_face.local.json'),'face_mode':face.get('mode'),'face_duration':face.get('duration_s'),
 'face_release_root':face.get('release_root'),'face_manifest_sha256':face.get('manifest_sha256'),
 'manual_state':m['state'],'automatic_following':m['automatic_following'],'readback':{k:r.get(k) for k in ('flags','width_us','target_us','lease_left_ms','epoch','ack_seq')},
 'zone':json.loads((Path('/home/root/aura-pan-current-20261024/da36c36a')/'face-zone-settings.json').read_text()),
 'motor_commands':0,'MMIO_opened':False}))
