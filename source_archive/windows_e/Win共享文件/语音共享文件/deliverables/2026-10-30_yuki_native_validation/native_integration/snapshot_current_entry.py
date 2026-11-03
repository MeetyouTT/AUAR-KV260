"""Read only current entry and curated public source; no API/device actions."""
from pathlib import Path
import hashlib,json,subprocess,zipfile
base=Path('/home/root/aura-yuki-validation-20261030');phase=base/'native_integration'
pid=subprocess.check_output(['systemctl','show','aura-avatar-ui.service','-p','MainPID','--value'],text=True).strip()
args=[x.decode() for x in Path('/proc',pid,'cmdline').read_bytes().split(b'\0') if x]
config_path=Path(args[args.index('--config')+1]);config=json.loads(config_path.read_text());runtime=Path(config['runtime']).resolve(strict=True)
assert str(runtime).startswith('/home/root/aura-board-vision-20261030/')
old=json.loads((phase/'board_source/manifest.json').read_text())
names=list(old['hashes'])+['aura/tools/board_avatar_pan.py']
hashes={};pins=config['component_sha256']
manifest=dict(runtime=str(runtime),pid=pid,ui_entry='aura/tools/board_avatar_pan.py',startup_config=str(config_path),
  startup_config_sha256=hashlib.sha256(config_path.read_bytes()).hexdigest(),component_pins=pins,
  launcher=str(config_path.parent/'launcher.py'),launcher_sha256=hashlib.sha256((config_path.parent/'launcher.py').read_bytes()).hexdigest(),
  original_basis=old,production_deployed_by_this_task=False)
launch=json.loads((runtime/'launch.json').read_text());manifest['child_pid']=str(launch['pid'])
manifest['child_cmdline']=Path('/proc',manifest['child_pid'],'cmdline').read_bytes().replace(b'\0',b' ').decode()
assert str(runtime/'aura/tools/board_avatar_pan.py') in manifest['child_cmdline']
with zipfile.ZipFile(phase/'board-source-current.zip','w',zipfile.ZIP_DEFLATED) as out:
    for name in names:
        path=runtime/name;assert path.is_file() and path.resolve().is_relative_to(runtime)
        data=path.read_bytes();hashes[name]=hashlib.sha256(data).hexdigest();out.writestr(name,data)
    manifest['hashes']=hashes
    out.writestr('manifest.json',json.dumps(manifest,indent=2))
print(json.dumps(dict(runtime=str(runtime),supervisor_pid=pid,child_pid=manifest['child_pid'],source_files=len(hashes),
  changed_from_initial=[name for name,h in old['hashes'].items() if hashes[name]!=h],component_pins=len(pins))))
