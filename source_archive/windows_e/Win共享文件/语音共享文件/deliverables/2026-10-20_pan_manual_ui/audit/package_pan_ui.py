"""Freeze additive manual UI sources and a no-actuation staging helper."""
import base64,gzip,hashlib,json,shutil
from pathlib import Path
J=Path(__file__).parent
AURA=Path('/home/ghmd/Win共享文件/语音共享文件/aura')
D=AURA.parent/'deliverables/2026-10-20_pan_manual_ui';D.mkdir(exist_ok=True)
inspect=Path(json.loads((J/'latest-axis-manual-ui-inspect.json').read_text())['evidence'])
startup=Path(json.loads((J/'latest-axis-manual-ui-startup.json').read_text())['evidence'])
cfg=json.loads((startup/'current-startup-config.json').read_text())
sha=lambda raw:hashlib.sha256(raw).hexdigest()
source=['board/motion/manual.py','board/motion/manual_vsrv.py','tools/pan_controls.py','tools/board_avatar_pan.py','tests/framework/test_manual_pan.py']
files={}
for rel in source:
 raw=(AURA/rel).read_bytes();compile(raw,rel,'exec');files[rel]={'base64':base64.b64encode(raw).decode(),'sha256':sha(raw)}
 p=D/'source'/rel;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(raw)
config={'schema_version':1,'boot_id':'3e1add36-b917-4289-91dc-699348528782','fdt_sha256':'501cf86ec839373df57862f829d34c8b5ab90a0eeeb6db0ac679bce831899929','driver_root':'/home/root/aura-adaptation-20261006/vsrv-source-14da0e60/unpacked'}
raw=(json.dumps(config,indent=2)+'\n').encode();files['config/pan_manual.local.json']={'base64':base64.b64encode(raw).decode(),'sha256':sha(raw)}
payload={'baseline':{'boot_id':config['boot_id'],'aura_root':cfg['runtime']+'/aura','gui_sha256':cfg['gui_sha256'],
 'startup_config_sha256':sha((startup/'current-startup-config.json').read_bytes()),'config_path':str(Path(cfg['runtime']).parent/'startup/config.json'),
 'launcher_path':str(Path(cfg['runtime']).parent/'startup/launcher.py'),'launcher_sha256':sha((startup/'current-startup-launcher.py').read_bytes())},'files':files}
raw=(json.dumps(payload,ensure_ascii=False,indent=2)+'\n').encode();deploy=(J/'board_pan_ui_deploy.py').read_bytes()
(D/'deployment-plan.json').write_text(json.dumps({'baseline':payload['baseline'],'new_files':{k:v['sha256'] for k,v in files.items()},'core_gui_preserved':True,'camera_restart':False,'gui_restart':True,'physical_test_commands':0,'midpoint_calibrated':False},ensure_ascii=False,indent=2)+'\n')
remote='/home/root/aura-pan-manual-ui-20261020/staged-v1'
stage='''"""Stage owned files only; no production changes or MMIO."""
import base64,gzip,hashlib,json
from pathlib import Path
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==%r
p=Path(%r);p.mkdir(parents=True,exist_ok=False)
for name,packed,expected in %r:
 raw=gzip.decompress(base64.b64decode(packed));assert hashlib.sha256(raw).hexdigest()==expected
 with (p/name).open('xb') as stream:stream.write(raw)
print(json.dumps({'status':'STAGED_NO_PRODUCTION_CHANGE_NO_ACTUATION','path':str(p)}),flush=True)
'''%(config['boot_id'],remote,[(n,base64.b64encode(gzip.compress(v,mtime=0)).decode(),sha(v)) for n,v in [('payload.json',raw),('deploy.py',deploy)]])
(J/'board_pan_ui_stage.py').write_text(stage)
launch='''"""Start one reviewed UI deployment; inspect results, never blindly retry."""
import hashlib,json,subprocess
from pathlib import Path
p=Path(%r);assert hashlib.sha256((p/'deploy.py').read_bytes()).hexdigest()==%r
with (p/'activation.json').open('x') as marker:
 with (p/'deployment.log').open('xb') as log:
  child=subprocess.Popen(['/usr/bin/python3','-B',str(p/'deploy.py')],stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
 value={'status':'LAUNCHED_ONCE_DO_NOT_RETRY','pid':child.pid,'path':str(p)}
 marker.write(json.dumps(value)+'\\n')
print(json.dumps(value),flush=True)
'''%(remote,sha(deploy))
(J/'board_pan_ui_activate.py').write_text(launch)
for n in ['board_pan_ui_stage.py','board_pan_ui_activate.py']:compile((J/n).read_bytes(),n,'exec')
print(json.dumps({'source_files':len(source),'new_runtime_files':len(files),'remote':remote,'payload_bytes':len(raw),'deployment_sha256':sha(deploy)}))
