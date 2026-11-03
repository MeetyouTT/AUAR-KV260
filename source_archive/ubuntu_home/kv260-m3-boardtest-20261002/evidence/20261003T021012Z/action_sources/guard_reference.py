import os,json,hashlib,subprocess,re
from pathlib import Path
WORK=Path('/home/root/kv260-zocl-repair-20261003T005805Z')
ORIGINAL_SHA='215fe760dafb6766545e308d8bc207c31712154fe5a8ed08342a101a5482a98d'
PARAMS={'enable_xgq_ert': '1'}
def digest(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def active_packages():
 text=subprocess.check_output(['dfx-mgr-client','-listPackage'],text=True)
 result=[]
 for line in text.splitlines():
  fields=line.split()
  if fields and re.fullmatch(r'-?\d+,?',fields[-1]):
   slot=int(fields[-1].rstrip(','))
   if slot!=-1: result.append((fields[0],slot))
 return result
def guard(expected,app):
 assert os.geteuid()==0 and os.uname().release=='5.15.36-xilinx-v2022.2','Unexpected root/kernel'
 assert Path('/sys/class/block/mmcblk1/device/cid').read_text().strip()=='0353445345333247805558c00401a100','Wrong test card'
 dev=os.stat('/').st_dev
 assert Path('/sys/dev/block/%d:%d'%(os.major(dev),os.minor(dev))).resolve().name=='mmcblk1p2','Wrong root partition'
 assert digest('/lib/modules/5.15.36-xilinx-v2022.2/extra/zocl.ko')==ORIGINAL_SHA,'Original module changed'
 if (WORK/'baseline/state.json').exists():
  saved=json.loads((WORK/'baseline/state.json').read_text())
  assert saved['boot_id']==Path('/proc/sys/kernel/random/boot_id').read_text().strip(),'Boot changed'
 m=Path('/sys/module/zocl')
 if expected is None: assert not m.exists(),'ZOCL unexpectedly loaded'
 else:
  assert (m/'srcversion').read_text().strip()==expected,'Wrong loaded module'
  assert int((m/'refcnt').read_text())==0 and not list((m/'holders').iterdir()),'ZOCL busy'
  assert {p.name:p.read_text().strip() for p in (m/'parameters').iterdir()}==PARAMS,'Module parameters changed'
 nodes={'/dev/dri/card1','/dev/dri/renderD128'}
 for p in Path('/sys/class/drm').iterdir():
  module=p/'device/driver/module'
  if module.exists() and str(module.resolve())=='/sys/module/zocl': nodes.add('/dev/dri/'+p.name)
 for proc in Path('/proc').iterdir():
  if not proc.name.isdigit(): continue
  try:
   for fd in (proc/'fd').iterdir():
    try: target=os.readlink(fd).split(' (deleted)')[0]
    except OSError: continue
    assert target not in nodes,'DRM client still open: PID '+proc.name
  except (FileNotFoundError,PermissionError): continue
 wanted=[] if app is None else [(app,0)]
 assert active_packages()==wanted,'Unexpected active packages'
def snapshot(label):
 print(label+'_UPTIME '+Path('/proc/uptime').read_text().strip(),flush=True)
 print(label+'_ACTIVE '+json.dumps(active_packages()),flush=True)
 print(label+'_DMESG_BEGIN',flush=True)
 subprocess.run(['dmesg'],check=True)
 print(label+'_DMESG_END',flush=True)
