"""Independently read back staged boot settings and the live driver value."""
import hashlib,json,subprocess
from pathlib import Path
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
backup=Path('/boot/aura-hdmi-delay5-20261021')
before=json.loads((backup/'before.json').read_text())
target=Path('/boot/uEnv.txt')
assert sha(target)==before['installed_uenv_sha256']
protected={p:sha(p) for p in before['protected_hashes']}
assert protected==before['protected_hashes']
assert sha('/boot/system.dtb')==before['original_dtb_sha256']
assert sha(backup/'boot.scr.before')==protected['/boot/boot.scr']
assert sha(backup/'system.dtb.before')==before['original_dtb_sha256']
compile((backup/'rollback.py').read_text(),str(backup/'rollback.py'),'exec')
param=Path('/sys/module/zynqmp_dpsub/parameters/power_on_delay_ms').read_text().strip()
cmdline=Path('/proc/cmdline').read_text().strip()
v={'boot_id':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),'uenv_sha256':sha(target),'uenv_text':target.read_text(),'runtime_delay_ms':param,'runtime_cmdline':cmdline,'next_boot_configuration_verified':True,'runtime_parameter_active':param=='5000' and 'zynqmp_dpsub.power_on_delay_ms=5000' in cmdline.split(),'protected_hashes':protected,'backup_verified':True,'rollback_sha256':sha(backup/'rollback.py'),'files_modified':0,'display_commands_sent':0,'movement_commands_sent':0}
v['units']=subprocess.check_output(['systemctl','show','aura-avatar-ui.service','aura-camera-ui.service','xserver-nodm.service','-p','Id','-p','MainPID','-p','ActiveState','-p','NRestarts'],text=True,timeout=5)
v['display']=subprocess.check_output(['env','DISPLAY=:0','xrandr','--current'],text=True,timeout=12)
edid=Path('/sys/class/drm/card0-DP-1/edid').read_bytes()
v['edid_bytes']=len(edid);v['edid_sha256']=hashlib.sha256(edid).hexdigest()
print(json.dumps(v),flush=True)
