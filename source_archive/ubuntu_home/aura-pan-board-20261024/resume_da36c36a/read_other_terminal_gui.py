import hashlib,json,subprocess,urllib.request
from pathlib import Path
uunit=subprocess.check_output(['systemctl','show','aura-avatar-ui.service','-p','MainPID','-p','ExecStart','--value'],text=True)
words=uunit.split()
cfgpath=next((Path(words[i+1]) for i,w in enumerate(words[:-1]) if w=='--config'),None)
assert cfgpath and cfgpath.is_file();cfg=json.loads(cfgpath.read_text());root=Path(cfg['runtime'])/'aura'
pins=cfg['component_sha256'];sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
assert all(sha(root/n)==h for n,h in pins.items())
op=urllib.request.build_opener(urllib.request.ProxyHandler({}))
with op.open('http://127.0.0.1:8783/api/state',timeout=3) as f:s=json.load(f)
m=s['manual_pan'];v=s.get('ui_runtime',{}).get('preview_metrics') or {}
editor=subprocess.run(['systemctl','show','aura-face-zone-editor.service','-p','MainPID','-p','ActiveState'],capture_output=True,text=True)
print(json.dumps({'gui_pid':subprocess.check_output(['systemctl','show','aura-avatar-ui.service','-p','MainPID','--value'],text=True).strip(),
 'unit_execstart':uunit,'config_sha256':sha(cfgpath),'runtime_root':str(root),'gui_component_pins':len(pins),
 'ui_page':s.get('ui_page'),'ui_layer':s.get('ui_layer'),'preview':v,'manual_state':m['state'],
 'automatic_following':m['automatic_following'],'manual_readback':m.get('readback'),
 'face_follow_component_present':'pan_face_follow' in Path(root/'tools/face_pan_controls.py').read_text(),
 'zone_editor_unit':editor.stdout,'zone_display':json.loads(Path('/home/root/aura-pan-current-20261024/da36c36a/face-zone-display-status.json').read_text()),
 'motor_commands':0,'MMIO_opened':False}))
