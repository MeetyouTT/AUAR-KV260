"""Enumerate supported display diagnostics; do not probe buses or write registers."""
import gzip,json,os,re,stat,subprocess
from pathlib import Path
v={'boot_id':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),'kernel':os.uname().release,'files_modified':0,'display_commands_sent':0,'movement_commands_sent':0}
v['connector_debugfs']=[]
for p in Path('/sys/kernel/debug/dri/0/DP-1').glob('*'):
 v['connector_debugfs'].append({'name':p.name,'mode':oct(stat.S_IMODE(p.stat().st_mode))})
v['module_parameters']={}
for p in Path('/sys/module').glob('*/parameters/*'):
 if p.name in ['power_on_delay_ms','aux_timeout_ms','edid_firmware']:
  v['module_parameters'][str(p)]={'value':p.read_text().strip(),'mode':oct(stat.S_IMODE(p.stat().st_mode))}
raw=gzip.decompress(Path('/proc/config.gz').read_bytes()).decode()
keys=['CONFIG_DRM_DP_AUX_CHARDEV','CONFIG_DRM_LOAD_EDID_FIRMWARE','CONFIG_DRM_ZYNQMP_DPSUB','CONFIG_DYNAMIC_DEBUG','CONFIG_DRM_DEBUG_SELFTEST']
v['config']={k:next((s for s in raw.splitlines() if s.startswith(k+'=') or s=='# '+k+' is not set'),'not found') for k in keys}
d=subprocess.check_output(['dmesg'],text=True)
v['recent_hardware_log']=[s for s in d.splitlines() if re.search(r'usb.*(disconnect|reset|over.current)|underflow|aux.*(fail|error|timeout)|link.*(fail|error)|training|display.*error',s,re.I)][-30:]
v['power_sensors']=[]
for p in Path('/sys/bus/iio/devices').glob('iio:device*'):
 name=p/'name'
 if name.exists() and 'ina260' in name.read_text():
  v['power_sensors'].append({'name':name.read_text().strip(),'path':str(p),'readings':{s.name:s.read_text().strip() for s in p.glob('in_*') if s.is_file() and s.name.endswith(('_raw','_input','_scale'))}})
print(json.dumps(v),flush=True)
