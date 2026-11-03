"""Read current pinned motion sources and kernel metadata. No driver imports/MMIO."""
import datetime,hashlib,json
from recovery_common import H,read,save,ssh
baseline=read('baseline.json')['board']
names=[name for name in baseline['pins'] if name in (
 'board/motion/manual_release.py','board/motion/manual_live_config.py','board/motion/manual_vsrv.py',
 'board/motion/rated_range_release.py','board/motion/current_reference_release.py',
 'config/pan_manual.local.json','config/pan_face.local.json','config/pan_direction.current.json')]
script=r'''
import hashlib,json
from pathlib import Path
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==BOOT
root=Path(ROOT)/'aura'
sources={}
for name in NAMES:
 p=root/name;raw=p.read_bytes();assert hashlib.sha256(raw).hexdigest()==PINS[name]
 sources[name]=raw.decode('utf-8')
read_errors=[]
def text(path):
 p=Path(path)
 try:return p.read_text().strip() if p.exists() else None
 except OSError as exc:
  read_errors.append({'path':str(p),'error':type(exc).__name__});return None
vart=Path('/etc/vart.conf');fdt=Path('/sys/firmware/fdt')
data={'boot':BOOT,'sources':sources,
 'fdt_sha256':hashlib.sha256(fdt.read_bytes()).hexdigest() if fdt.exists() else None,
 'vart_config':text(vart),'vart_sha256':hashlib.sha256(vart.read_bytes()).hexdigest() if vart.exists() else None,
 'fpga':{key:text('/sys/class/fpga_manager/fpga0/'+key) for key in ('name','state','firmware')},
 'read_errors':read_errors,'register_io':False,'driver_imported':False,'configuration_changed':False}
pid=PID;children=text('/proc/'+pid+'/task/'+pid+'/children') or ''
data['motion_arguments']=[]
for process in [pid]+children.split():
 args=Path('/proc/'+process+'/cmdline').read_bytes().decode().split('\0')
 selected=[]
 for i,arg in enumerate(args):
  if arg.startswith('--') and any(k in arg for k in ('pan','motion','mechanic','manual')):
   selected.append(arg)
   if i+1<len(args) and not args[i+1].startswith('--'):selected.append(args[i+1])
 if selected:data['motion_arguments'].append({'pid':process,'arguments':selected})
print(json.dumps(data))
'''.replace('BOOT',repr(baseline['boot'])).replace('ROOT',repr(baseline['actual_runtime'])).replace('PINS',repr(baseline['pins'])).replace('NAMES',repr(names)).replace('PID',repr(baseline['ui_service']['MainPID']))
data=json.loads(ssh('python3 -B -',script,timeout=20));sources=data.pop('sources')
for name,source in sources.items():
 path=H/'motion_source_snapshot'/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_text(source,encoding='utf-8')
data.update(checked_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
 source_sha256={name:hashlib.sha256(source.encode()).hexdigest() for name,source in sources.items()})
save('motion_platform.json',data)
print(json.dumps(data,ensure_ascii=True))
