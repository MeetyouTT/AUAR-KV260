"""Board-only guards and evidence helpers for this independent controlled run."""
import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import socket
import subprocess
import time

WORK = Path('/home/root/kv260-runtime-live-20261003T082232Z')
CFG = json.loads((WORK/'config.json').read_text())

def digest(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda:stream.read(1048576),b''):
            h.update(block)
    return h.hexdigest()

def run(argv, timeout=90):
    p=subprocess.run(argv,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=timeout)
    assert p.returncode==0, '{} returned {}: {}'.format(argv,p.returncode,p.stdout)
    return p.stdout

def active_packages():
    result=[]
    for line in run(['dfx-mgr-client','-listPackage'],30).splitlines():
        words=line.split()
        if words and re.fullmatch(r'-?\d+,?',words[-1]):
            slot=int(words[-1].rstrip(','))
            if slot!=-1:result.append((words[0],slot))
    return result

def identity_guard():
    assert os.geteuid()==0 and os.uname().release=='5.15.36-xilinx-v2022.2'
    assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==CFG['boot_id'],'Boot changed'
    assert Path('/sys/class/block/mmcblk1/device/cid').read_text().strip()=='0353445345333247805558c00401a100','Card changed'
    dev=os.stat('/').st_dev
    assert Path('/sys/dev/block/%d:%d'%(os.major(dev),os.minor(dev))).resolve().name=='mmcblk1p2'

def files_guard(include_vart=False):
    for path,expected in CFG['stock_hashes26'].items():
        if include_vart or path!='/etc/vart.conf':
            assert digest(path)==expected,'Original file changed: '+path

def drm_guard():
    nodes=set(CFG['zocl_drm_nodes'])
    for node in Path('/sys/class/drm').iterdir():
        module=node/'device/driver/module'
        if module.exists() and module.resolve()==Path('/sys/module/zocl'):
            nodes.add('/dev/dri/'+node.name)
    for proc in Path('/proc').iterdir():
        if not proc.name.isdigit():continue
        try:
            for fd in (proc/'fd').iterdir():
                try:target=os.readlink(fd)
                except FileNotFoundError:continue
                assert target.split(' (deleted)')[0] not in nodes,'ZOCL DRM client open: '+proc.name+' '+target
        except FileNotFoundError:continue

def guard(driver,app):
    identity_guard();files_guard();drm_guard()
    mod=Path('/sys/module/zocl')
    if driver is None:
        assert not mod.exists(),'Driver unexpectedly loaded'
    else:
        assert (mod/'srcversion').read_text().strip()==driver,'Unexpected driver'
        assert int((mod/'refcnt').read_text())==0 and not list((mod/'holders').iterdir()),'Driver busy'
        assert {p.name:p.read_text().strip() for p in (mod/'parameters').iterdir()}=={'enable_xgq_ert':'1'}
    assert active_packages()==([] if app is None else [(app,0)]),'Unexpected active app'
    if app is not None:
        assert Path('/sys/class/fpga_manager/fpga0/state').read_text().strip()=='operating'
        assert Path('/proc/device-tree/fpga-full/firmware-name').read_bytes().rstrip(b'\0').decode()==app+'.bit.bin'
        assert Path('/etc/vart.conf').read_text()=='firmware: /lib/firmware/xilinx/'+app+'/'+app+'.xclbin\n'

gate=guard

def manager_pid():
    return int(run(['systemctl','show','dfx-mgr.service','--property=MainPID','--value'],30).strip())

def manager_errors():
    path=WORK/'candidate-manager.log'
    return [line for line in path.read_text(errors='replace').splitlines() if 'ERROR:' in line] if path.exists() else []

def manager_guard(candidate):
    pid=manager_pid()
    assert pid>0 and run(['systemctl','is-active','dfx-mgr.service'],30).strip()=='active'
    expected=CFG['candidate_manager'] if candidate else '/usr/bin/dfx-mgrd'
    assert os.readlink('/proc/%d/exe'%pid)==expected,'Unexpected manager process'
    assert digest(expected)==(CFG['manager_sha256'] if candidate else CFG['stock_hashes26']['/usr/bin/dfx-mgrd'])
    drops=run(['systemctl','show','dfx-mgr.service','--property=DropInPaths','--value'],30).strip()
    if candidate:
        assert drops==CFG['override'] and digest(drops)==CFG['override_text_sha256'],'Unexpected service override'
        assert not manager_errors(),'Candidate manager reported ERROR'
    else:assert not drops,'Original manager has overrides'

def wait_manager(candidate):
    for _ in range(100):
        if manager_pid()>0:
            s=socket.socket(socket.AF_UNIX,socket.SOCK_SEQPACKET)
            try:ready=s.connect_ex('/tmp/dfx-mgrd.socket')==0
            finally:s.close()
            if ready:
                manager_guard(candidate)
                return
        time.sleep(.1)
    raise RuntimeError('Manager did not become ready via SOCK_SEQPACKET')

def watches():
    count=0
    for p in (Path('/proc')/str(manager_pid())/'fdinfo').iterdir():
        try:count+=p.read_text().count('inotify wd:')
        except FileNotFoundError:continue
    return count

def snapshot(label):
    identity_guard()
    stamp=datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    directory=WORK/'logs';directory.mkdir(exist_ok=True)
    kernel=run(['dmesg'],30)
    kernel_path=directory/(stamp+'-'+label+'-kernel.log')
    kernel_path.write_text(kernel)
    pid=manager_pid()
    data={'label':label,'utc':stamp,'uptime':Path('/proc/uptime').read_text().strip(),'active':active_packages(),
          'driver':Path('/sys/module/zocl/srcversion').read_text().strip() if Path('/sys/module/zocl').exists() else None,
          'manager_pid':pid,'watches':watches() if pid>0 else None,
          'kernel_log':str(kernel_path),'kernel_sha256':digest(kernel_path),
          'meminfo':Path('/proc/meminfo').read_text(),'slabinfo':Path('/proc/slabinfo').read_text(),
          'manager_status':Path('/proc/%d/status'%pid).read_text() if pid>0 else None,
          'manager_errors':manager_errors()}
    (directory/(stamp+'-'+label+'-snapshot.json')).write_text(json.dumps(data,indent=2))
    print('SNAPSHOT '+json.dumps({k:v for k,v in data.items() if k not in ['meminfo','slabinfo','manager_status']}),flush=True)
    return data
