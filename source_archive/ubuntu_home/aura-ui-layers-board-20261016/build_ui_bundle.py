"""Build the exact GUI delta against a fresh read of the installed release."""
import hashlib
import io
import json
from pathlib import Path
import zipfile

WORK=Path(__file__).resolve().parent
AURA=Path('/home/ghmd/Win共享文件/共享文件夹/aura')
inventory_dir=sorted((WORK/'evidence').glob('*-update-inventory'))[-1]
inventory=json.loads((inventory_dir/'response.json').read_text())
config=json.loads((inventory_dir/'installed_config.json').read_text())
files={'aura/'+name:(AURA/name).read_bytes() for name in inventory['files']}
runtime={name:{'before_sha256':row['sha256']} for name,row in inventory['files'].items()}
for name,data in files.items():
    relative=name[5:]
    if relative=='tools/board_avatar_gtk.py':config['gui_sha256']=hashlib.sha256(data).hexdigest()
    else:config['component_sha256'][relative]=hashlib.sha256(data).hexdigest()
launcher=(AURA/'scripts/board_ui_startup/launcher.py').read_bytes()
configuration=(json.dumps(config,indent=2)+'\n').encode()
startup_id=hashlib.sha256(launcher+configuration).hexdigest()[:16]
startup_release='/home/root/aura-ui-startup-20261009/releases/'+startup_id
unit=(AURA/'scripts/board_ui_startup/aura-avatar-ui.service.in').read_text().replace('@INSTALL_DIR@',startup_release).encode()
files.update({'startup/launcher.py':launcher,'startup/config.json':configuration,
              'startup/aura-avatar-ui.service':unit,'board_deploy.py':(WORK/'board_deploy.py').read_bytes()})
rows={name:{'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()} for name,data in sorted(files.items())}
update_id=hashlib.sha256(json.dumps(rows,sort_keys=True).encode()).hexdigest()[:16]
manifest={'update_id':update_id,'runtime':inventory['runtime'],'expected_boot_id':inventory['boot_id'],
          'old_unit_sha256':hashlib.sha256((inventory_dir/'installed_ui.service').read_bytes()).hexdigest(),
          'startup_release':startup_release,'runtime_files':runtime,'files':rows}
stream=io.BytesIO()
with zipfile.ZipFile(stream,'w',zipfile.ZIP_DEFLATED) as z:
    for name,data in files.items():z.writestr(name,data)
    z.writestr('manifest.json',json.dumps(manifest,indent=2)+'\n')
blob=stream.getvalue()
archive=WORK/('ui-layers-'+update_id+'.zip')
with archive.open('xb') as f:f.write(blob)
record={'release_id':update_id,'zip':archive.name,'bytes':len(blob),'sha256':hashlib.sha256(blob).hexdigest(),
        'board_root':'/home/root/aura-ui-layers-20261016/update-'+update_id,'files':rows}
(WORK/'capture_bundle.json').write_text(json.dumps(record,indent=2)+'\n')
(WORK/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
print(json.dumps({key:record[key] for key in ('release_id','zip','bytes','board_root')}))
