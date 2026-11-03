import hashlib,json,subprocess,urllib.request
from pathlib import Path
R=Path('/home/root/aura-pan-current-20261024/16a07283');G=Path('/home/root/aura-pan-current-20261024/463c9307/gui-face-edge-v5');A=G/'runtime/aura'
o=urllib.request.build_opener(urllib.request.ProxyHandler({}))
def get(port,path):
 with o.open('http://127.0.0.1:%d%s'%(port,path),timeout=3) as r:return json.load(r)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
s=json.loads((R/'state.json').read_text());human=json.loads((R/'relative-20us-human-observation.json').read_text())
boot=Path('/proc/sys/kernel/random/boot_id').read_text().strip();assert boot==s['boot']==human['boot_id']
cfg=json.loads((G/'startup/config.json').read_text());assert all(sha(A/p)==v for p,v in cfg['component_sha256'].items())
h=get(8790,'/health');u=get(8783,'/api/state');d=h['dpu_schedule']
manual=json.loads((A/'config/pan_manual.local.json').read_text());face=json.loads((A/'config/pan_face.local.json').read_text())
print(json.dumps({'boot':boot,'state_phase':s['phase'],'camera_pid':h['pid'],'identity_ready':h['identity']['ready'],
 'owner_fenced':d['owner_fenced'],'primary_overruns':d['primary_period_overruns'],'optional_overruns':{k:d['optional'][k]['overruns'] for k in ('sface','yunet')},
 'manual':u['manual_pan'],'gui_pid':subprocess.check_output(['systemctl','show','aura-avatar-ui.service','-p','MainPID','--value'],text=True).strip(),
 'startup_config_sha256':sha(G/'startup/config.json'),'pins':len(cfg['component_sha256']),
 'manual_config':manual,'face_config':face,'entry_source':(A/'tools/board_avatar_pan.py').read_text(),
 'manual_release_source_sha256':sha(A/'board/motion/manual_release.py'),
 'center':json.loads((R/'center-reference.json').read_text()),'observation':human,'MMIO_opened':False,'motor_commands_sent':0}))
