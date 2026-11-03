import base64,hashlib,json,urllib.request
from pathlib import Path
cfg=Path('/home/root/aura-speech-motion-20261021/de989bf024a9/startup/config.json')
assert hashlib.sha256(cfg.read_bytes()).hexdigest()=='6c47003c4d020066a3ba4c9daa8f905101d633c4cf507951bea3ac3ca86a161d'
d=json.loads(cfg.read_text());runtime=Path(d['runtime']);launcher=cfg.parent/'launcher.py'
out={'read_only':True,'boot':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
 'gui_runtime':str(runtime),'config_keys':list(d),
 'runtime_entries':[{'name':p.name,'symlink':p.is_symlink(),'directory':p.is_dir()} for p in sorted(runtime.iterdir())],
 'launcher':{'sha256':hashlib.sha256(launcher.read_bytes()).hexdigest(),'base64':base64.b64encode(launcher.read_bytes()).decode()},
 'gui_source_tree_python_files':sum(1 for p in (runtime/'aura').rglob('*.py'))}
op=urllib.request.build_opener(urllib.request.ProxyHandler({}))
with op.open('http://127.0.0.1:8783/api/state',timeout=3) as response:u=json.load(response)
hands=u.get('handsfree_dialogue') or {}
out['ui']={k:u.get(k) for k in ('phase','playing','paused','audio_output_state')}
out['microphone_open']=hands.get('microphone_open');out['handsfree_enabled']=hands.get('enabled')
out['manual_pan_state']=(u.get('manual_pan') or {}).get('state')
print(json.dumps(out))
