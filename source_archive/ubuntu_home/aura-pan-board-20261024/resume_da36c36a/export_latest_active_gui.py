import base64,hashlib,json,re,subprocess,urllib.request
from pathlib import Path
raw=subprocess.check_output(['systemctl','show','aura-avatar-ui.service','-p','ExecStart','-p','MainPID','-p','DropInPaths'],text=True)
props=dict(x.split('=',1) for x in raw.splitlines() if '=' in x)
match=re.search(r'--config (/[^ ;]+)',props['ExecStart']);assert match
path=Path(match.group(1));assert str(path).startswith('/home/root/aura-animation-dialogue-20261026/')
cfg=json.loads(path.read_text());A=Path(cfg['runtime'])/'aura'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
assert all(sha(A/n)==v for n,v in cfg['component_sha256'].items())
names=['board/motion/manual_vsrv.py','board/motion/manual_live_config.py','board/motion/manual_release.py','board/motion/follow_readback.py','tools/face_pan_controls.py']
files={n:{'sha256':sha(A/n),'base64':base64.b64encode((A/n).read_bytes()).decode()} for n in names}
print(json.dumps({'startup':cfg,'startup_path':str(path),'startup_sha256':sha(path),'active_root':str(path.parent.parent),
 'gui_pid':int(props['MainPID']),'dropins':props['DropInPaths'],'files':files,
 'manual_config':json.loads((A/'config/pan_manual.local.json').read_text()),
 'face_config':json.loads((A/'config/pan_face.local.json').read_text()),'motor_commands':0,'MMIO_opened':False}))
