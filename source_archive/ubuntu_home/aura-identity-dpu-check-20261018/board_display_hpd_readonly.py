"""Read connector and optional AUX link status; no writes or forced detect."""
import base64,hashlib,json,os,subprocess
from pathlib import Path
v={'boot_id':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
   'display_commands_sent':0,'movement_commands_sent':0,'files_modified':0}
root=Path('/sys/class/drm/card0-DP-1')
raw=(root/'edid').read_bytes()
v['connector']={'status':(root/'status').read_text().strip(),'edid_bytes':len(raw),
  'edid_sha256':hashlib.sha256(raw).hexdigest(),'edid_base64':base64.b64encode(raw).decode()}
v['aux_devices']=[]
for p in Path('/dev').glob('drm_dp_aux*'):
    row={'path':str(p)}
    try:
        fd=os.open(str(p),os.O_RDONLY|os.O_CLOEXEC)
        try:
            row['receiver_caps_000']=os.pread(fd,16,0).hex()
            row['link_config_100']=os.pread(fd,2,0x100).hex()
            row['link_status_200']=os.pread(fd,8,0x200).hex()
            row['branch_id_500']=os.pread(fd,12,0x500).hex()
        finally:os.close(fd)
    except OSError as exc:row['error']=str(exc)
    v['aux_devices'].append(row)
v['debugfs_names']=[str(p.relative_to('/sys/kernel/debug/dri/0')) for p in Path('/sys/kernel/debug/dri/0').glob('*')]
v['i2c_bound_devices']=[]
for p in Path('/sys/bus/i2c/devices').glob('*-*'):
    if (p/'name').exists():
        row={'device':p.name,'name':(p/'name').read_text().strip()}
        if (p/'driver').exists():row['driver']=str((p/'driver').resolve())
        v['i2c_bound_devices'].append(row)
p=Path('/proc/interrupts')
v['display_interrupts']=[line for line in p.read_text().splitlines() if any(word in line.lower() for word in ['display','dpdma','dp.aux','zynqmp-dp'])]
print(json.dumps(v),flush=True)
