import hashlib,json,subprocess,urllib.request
from pathlib import Path
o=urllib.request.build_opener(urllib.request.ProxyHandler({}))
with o.open('http://127.0.0.1:8783/api/state',timeout=3) as r:s=json.load(r)
cfg=Path('/home/root/aura-speech-motion-20261021/de989bf024a9/startup/config.json');c=json.loads(cfg.read_text())
marker=Path(c['display_recovery_marker']);m=json.loads(marker.read_text()) if marker.exists() else {}
boot=Path('/proc/sys/kernel/random/boot_id').read_text().strip()
out={'boot':boot,'phase':s['phase'],'playing':s['playing'],'pending_job':s.get('pending_job') is not None,'recording_state':s.get('local_recording',{}).get('state'),
 'manual_pan':s.get('manual_pan'),'monitor_preference':None,'launcher_display_retrain_needed':bool(c.get('startup_display_retrain',False)) and any(m.get(k)!=v for k,v in {'boot_id':boot,'output':c['output'],'mode':c['mode'],'edid_sha256':c['edid_sha256']}.items()),'settings_files':[]}
p=Path('/home/root/.local/share/aura/handsfree_dialogue.json')
if p.exists():out['monitor_preference']=json.loads(p.read_text())
root=Path(c['runtime'])
for p in sorted(root.glob('avatar*settings.json')):
 out['settings_files'].append({'path':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
out['launcher_preflight']=subprocess.check_output(['/usr/bin/python3','-B',str(cfg.parent/'launcher.py'),'--config',str(cfg),'--preflight'],timeout=10).decode().strip()
print(json.dumps(out))
