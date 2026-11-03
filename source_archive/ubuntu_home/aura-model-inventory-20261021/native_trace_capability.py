import gzip,json,os,shutil
from pathlib import Path
paths=['/sys/kernel/tracing','/sys/kernel/tracing/uprobe_events','/sys/kernel/debug/tracing',
 '/sys/kernel/debug/tracing/uprobe_events','/sys/bus/event_source/devices/uprobe/type','/proc/config.gz']
result={path:{'exists':Path(path).exists(),'readable':os.access(path,os.R_OK),'writable':os.access(path,os.W_OK)} for path in paths}
result['tools']={name:shutil.which(name) for name in ('perf','bpftrace','objdump','readelf')}
config=Path('/proc/config.gz')
if config.exists():
 text=gzip.decompress(config.read_bytes()).decode()
 keys=('CONFIG_UPROBES=','CONFIG_UPROBE_EVENTS=','CONFIG_PERF_EVENTS=','CONFIG_FTRACE=','CONFIG_KPROBE_EVENTS=','CONFIG_BPF=')
 result['kernel_options']=[line for line in text.splitlines() if line.startswith(keys)]
result['boot']=Path('/proc/sys/kernel/random/boot_id').read_text().strip()
print(json.dumps(result))
