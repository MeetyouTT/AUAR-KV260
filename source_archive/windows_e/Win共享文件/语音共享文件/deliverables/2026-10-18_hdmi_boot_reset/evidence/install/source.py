"""Persist the 2-second boot display reset; do not restart current services."""
import base64,hashlib,json,os,shutil,stat,subprocess
from pathlib import Path
assert Path('/sys/block/mmcblk1/device/cid').read_text().strip()=='0353445345333247805558c00401a100'
root=Path('/home/root/aura-automatic-conversation-20261018/candidate-b1b08f8b0b2b')
config=root/'startup/config.json';launcher=root/'startup/launcher.py'
assert not config.is_symlink()
before=config.read_bytes();expected='b94b4522021c875bda4e9b414e82f52ae9bad00ce4bbc8892c29e4ddc466c0f2'
assert hashlib.sha256(before).hexdigest()==expected
assert hashlib.sha256(launcher.read_bytes()).hexdigest()=='61d852c0fd02077c0d6d167516cad90401e49551ff0e64f7e3fcaca3dcba932d'
def run(args):
 p=subprocess.run(args,env=dict(os.environ,DISPLAY=':0'),stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=12)
 assert p.returncode==0,(args,p.stdout[-1000:])
 return p.stdout.strip()
assert run(['systemctl','is-enabled','aura-avatar-ui.service'])=='enabled'
assert run(['systemctl','show','aura-avatar-ui.service','-p','WorkingDirectory','--value'])==str(root/'runtime/aura')
boot=Path('/proc/sys/kernel/random/boot_id').read_text().strip()
pids={name:run(['systemctl','show',name,'-p','MainPID','--value']) for name in ['aura-avatar-ui.service','aura-camera-ui.service']}
value=json.loads(before);assert value['startup_display_retrain'] is True and value['display_retrain_off_seconds']==1
value['display_retrain_off_seconds']=2
after=(json.dumps(value,ensure_ascii=False,indent=2)+'\n').encode()
backup=config.with_name('config.before-hdmi-boot-reset-20261018.json')
assert not backup.exists();shutil.copy2(config,backup)
candidate=config.with_name('config.hdmi-boot-reset-20261018.candidate.json')
assert not candidate.exists()
with candidate.open('xb') as stream:stream.write(after);stream.flush();os.fsync(stream.fileno())
os.chmod(candidate,stat.S_IMODE(config.stat().st_mode))
preflight=run(['python3','-B',str(launcher),'--config',str(candidate),'--preflight'])
assert hashlib.sha256(config.read_bytes()).hexdigest()==expected
os.replace(str(candidate),str(config))
try:
 assert config.read_bytes()==after
 run(['python3','-B',str(launcher),'--config',str(config),'--preflight'])
 assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==boot
 for name,pid in pids.items():assert run(['systemctl','show',name,'-p','MainPID','--value'])==pid
except Exception:
 restore=config.with_name('config.hdmi-restore-'+str(os.getpid()))
 shutil.copy2(backup,restore);os.replace(str(restore),str(config));raise
edid=Path('/sys/class/drm/card0-DP-1/edid').read_bytes()
report={'status':'PASS_PERSISTED_NEXT_BOOT_HDMI_RESET_2S','config_path':str(config),'backup_path':str(backup),
 'boot_id':boot,'service_pids_unchanged':pids,'preflight':preflight,
 'display_retrain_off_seconds':2,'startup_display_retrain':True,'service_enabled':True,
 'warm_reboot_configured':True,'cold_boot_configured':True,'reboot_performed':False,
 'physical_cold_boot_verified':False,'current_edid_bytes':len(edid),
 'config_sha256_before':expected,'config_sha256_after':hashlib.sha256(after).hexdigest(),
 'artifacts':{'installed-startup-config.json':{'base64':base64.b64encode(after).decode(),'sha256':hashlib.sha256(after).hexdigest()}}}
(root/'startup/hdmi-boot-reset-20261018.json').write_text(json.dumps({k:v for k,v in report.items() if k!='artifacts'},indent=2)+'\n')
print(json.dumps(report),flush=True)
