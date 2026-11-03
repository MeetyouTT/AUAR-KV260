import base64,hashlib,json,os
from pathlib import Path
root=Path('/home/root/aura-video-cpu-20261023/66cde810eb059dce/runtime')
files=['board/motion/manual.py','board/motion/manual_vsrv.py','board/motion/manual_process.py',
 'board/motion/vsrv_driver.py','board/motion/vsrv_transport.py','tools/pan_controls.py','tools/board_avatar_pan.py']
out={}
for name in files:
 p=root/'aura'/name
 if not p.exists():out[name]={'exists':False};continue
 raw=p.read_bytes();out[name]={'exists':True,'sha256':hashlib.sha256(raw).hexdigest(),'base64':base64.b64encode(raw).decode()}
inventory=[]
for p in root.iterdir():
 inventory.append({'name':p.name,'symlink':p.is_symlink(),'directory':p.is_dir()})
result={'boot':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),'root':str(root),'files':out,'runtime_entries':inventory,
 'gui_python_manifest':{str(p.relative_to(root/'aura')):hashlib.sha256(p.read_bytes()).hexdigest() for p in (root/'aura').rglob('*.py') if not p.is_symlink()},
 'aura_top_entries':[{'name':p.name,'symlink':p.is_symlink(),'directory':p.is_dir()} for p in (root/'aura').iterdir()],
 'settings_files':[{'path':str(p.relative_to(root)),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in root.glob('*settings*.json') if p.is_file()]}
print(json.dumps(result))
