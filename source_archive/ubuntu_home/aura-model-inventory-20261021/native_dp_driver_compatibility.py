import gzip,hashlib,json,os,subprocess
from pathlib import Path
wanted={'register_kprobe','unregister_kprobe','drm_mode_getresources','zynqmp_dp_irq_handler','zynqmp_dp_train_loop'}
names={}
for row in Path('/proc/kallsyms').read_text().splitlines():
 f=row.split()
 if len(f)>=3 and f[2] in wanted:names[f[2]]=f[1]
config=gzip.decompress(Path('/proc/config.gz').read_bytes()).decode()
keys=['CONFIG_MODULES','CONFIG_MODULE_UNLOAD','CONFIG_KPROBES','CONFIG_MODVERSIONS','CONFIG_MODULE_SIG','CONFIG_ARM64','CONFIG_DRM_ZYNQMP_DPSUB','CONFIG_DEBUG_INFO_BTF','CONFIG_CFI_CLANG']
flags={k:next((line for line in config.splitlines() if line.startswith(k+'=') or line=='# '+k+' is not set'),None) for k in keys}
dev=Path('/sys/bus/platform/devices/fd4a0000.display')
print(json.dumps({'boot':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),'release':os.uname().release,
 'version':Path('/proc/version').read_text().strip(),'driver':str((dev/'driver').resolve()),
 'drm_card0_device':str(Path('/sys/class/drm/card0/device').resolve()),
 'kernel_config_flags':flags,'required_symbol_names_only':names,
 'modetest':subprocess.run(['which','modetest'],capture_output=True,text=True).stdout.strip(),
 'existing_probe_definitions':Path('/sys/kernel/tracing/kprobe_events').read_text().strip(),
 'own_instances':[p.name for p in Path('/sys/kernel/tracing/instances').iterdir() if p.name.startswith('aura_hdmi_')]}))
