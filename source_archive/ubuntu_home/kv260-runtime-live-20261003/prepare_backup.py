#!/usr/bin/env python3
import json
from prepare_live import ROOT, manifest

cfg=json.loads((ROOT/'config.json').read_text())
work=cfg['work']
identity="""import os,json,hashlib,subprocess,shutil
from pathlib import Path
WORK=Path(%r)
assert os.geteuid()==0 and os.uname().release=='5.15.36-xilinx-v2022.2'
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==%r
assert Path('/sys/class/block/mmcblk1/device/cid').read_text().strip()=='0353445345333247805558c00401a100'
assert Path('/sys/module/zocl/srcversion').read_text().strip()=='0991D1B457855C8987936E6'
assert Path('/sys/module/zocl/refcnt').read_text().strip()=='0'
assert shutil.disk_usage('/home/root').free>1073741824
"""%(work,cfg['boot_id'])
create=identity+"""WORK.mkdir(exist_ok=False)
b=WORK/'baseline';b.mkdir();(b/'files').mkdir()
state={'boot_id':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),'card_cid':Path('/sys/class/block/mmcblk1/device/cid').read_text().strip(),'kernel':os.uname().release,'active_raw':subprocess.check_output(['dfx-mgr-client','-listPackage'],text=True),'service':subprocess.check_output(['systemctl','show','dfx-mgr.service'],text=True),'parameters':{'enable_xgq_ert':Path('/sys/module/zocl/parameters/enable_xgq_ert').read_text().strip()},'root_free':shutil.disk_usage('/').free}
(b/'state.json').write_text(json.dumps(state,indent=2))
(b/'kernel.log').write_bytes(subprocess.check_output(['dmesg']))
(b/'dfx-journal.log').write_bytes(subprocess.check_output(['journalctl','-u','dfx-mgr.service','--no-pager','-o','short-monotonic']))
(b/'fstab').write_bytes(Path('/etc/fstab').read_bytes())
print('NEW_BACKUP '+json.dumps(state),flush=True)
"""
entries=[('create',create,180)]
items=list(cfg['stock_hashes26'].items())
for index in range(0,len(items),9):
    expected=dict(items[index:index+9])
    body=identity+"expected="+repr(expected)+"\n"+"""actual={}
for path,sha in expected.items():
 p=Path(path);data=p.read_bytes();assert hashlib.sha256(data).hexdigest()==sha,path
 dest=WORK/'baseline/files'/path.lstrip('/');dest.parent.mkdir(parents=True,exist_ok=True)
 assert not dest.exists();shutil.copy2(path,str(dest))
 assert hashlib.sha256(dest.read_bytes()).hexdigest()==sha
 actual[path]={'bytes':len(data),'sha256':sha,'backup':str(dest)}
print('BACKUP_FILES '+json.dumps(actual),flush=True)
"""
    entries.append(('files-'+str(index//9),body,180))
manifest('backup',entries)
