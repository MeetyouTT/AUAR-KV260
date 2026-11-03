"""Read-only prerequisites for the authorized powered bench test."""
import hashlib,json,subprocess
from pathlib import Path
boot=Path('/proc/sys/kernel/random/boot_id').read_text().strip()
assert boot=='f7a3ff07-fc20-4804-af12-c314a7a1847a','Boot changed; inspect before deployment'
def run(argv):
 p=subprocess.run(argv,capture_output=True,text=True,timeout=12)
 return {'rc':p.returncode,'out':p.stdout,'err':p.stderr}
root=Path('/home/root/aura-realtime-vision-20261007')
current=json.loads((root/'current.json').read_text())
print(json.dumps({'boot_id':boot,'fpga_state':Path('/sys/class/fpga_manager/fpga0/state').read_text().strip(),
 'firmware':Path('/proc/device-tree/fpga-full/firmware-name').read_bytes().rstrip(b'\0').decode(),
 'base_dt_sha256':hashlib.sha256(Path('/sys/firmware/fdt').read_bytes()).hexdigest(),
 'zocl_refs':Path('/sys/module/zocl/refcnt').read_text().strip(),
 'accelerator_clients':{str(p):p.read_text() for p in Path('/sys/kernel/debug/dri').glob('*/clients') if p.parent.name!='0'},
 'network':run(['ip','-brief','address']),
 'mounts':[s for s in Path('/proc/mounts').read_text().splitlines() if 'nfs' in s or 'cifs' in s],
 'manager':run(['systemctl','is-active','dfx-mgr']),
 'apps':run(['xmutil','listapps']),
 'preview_pid':current['pid'],'preview_status':json.loads((Path(current['run_root'])/'status.json').read_text()),
 'vart_conf':Path('/etc/vart.conf').read_text(),
 'powered_test_authorized':True,'cutoff_protection':'USER_REPORTED_NOT_VERIFIED','motion_emitted':False},indent=2))
