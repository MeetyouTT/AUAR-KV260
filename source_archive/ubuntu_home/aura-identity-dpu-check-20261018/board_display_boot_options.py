"""Read display boot capabilities, no configuration changes."""
import gzip,json,os
from pathlib import Path
v={'boot_id':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
   'display_commands_sent':0,'movement_commands_sent':0,'files_modified':0}
kernel=os.uname().release
for source in [Path('/proc/config.gz'),Path('/boot/config-'+kernel)]:
    if not source.exists():continue
    raw=gzip.decompress(source.read_bytes()).decode() if source.suffix=='.gz' else source.read_text()
    v['kernel_config_source']=str(source)
    keys=['CONFIG_DRM_LOAD_EDID_FIRMWARE','CONFIG_FW_LOADER','CONFIG_DRM_ZYNQMP_DPSUB','CONFIG_DRM_XLNX','CONFIG_XILINX_DPDMA']
    v['kernel_options']={key:next((line for line in raw.splitlines() if line.startswith(key+'=') or line=='# '+key+' is not set'),'not found') for key in keys}
    break
v['edid_override_parameters']={}
for name in ['/sys/module/drm/parameters/edid_firmware','/sys/module/drm_kms_helper/parameters/edid_firmware']:
    p=Path(name)
    if p.exists():v['edid_override_parameters'][name]=p.read_text().strip()
p=Path('/etc/X11/xorg.conf')
if p.exists():v['xorg_config']=p.read_text()[:5000]
v['edid_now_bytes']=len(Path('/sys/class/drm/card0-DP-1/edid').read_bytes())
print(json.dumps(v),flush=True)
