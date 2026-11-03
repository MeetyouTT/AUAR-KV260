#!/usr/bin/env python3
"""Reuse a hash-verified board archive in a fresh session after reboot; no MMIO."""
import base64
import datetime
import gzip
import importlib.util
import json
from pathlib import Path
import shlex

ROOT=Path(__file__).resolve().parents[1]
previous=json.loads((ROOT/'CURRENT_BOARD_STAGE.json').read_text())
assert previous['complete']
tag=datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')
out=ROOT/'evidence'/(tag+'-uart-restage')
out.mkdir(exist_ok=False)
dest='/home/root/aura-pin3-static-stage/'+tag+'/aura-pin3-static-stage.tar.gz'
source=r'''
import hashlib,json,os,subprocess,sys
from pathlib import Path
assert os.uname().machine=='aarch64' and os.geteuid()==0
assert Path('/sys/block/mmcblk1/device/cid').read_text().strip()=='0353445345333247805558c00401a100'
assert Path('/proc/device-tree/fpga-full/firmware-name').read_bytes().rstrip(b'\0')==b'kv260-benchmark-b4096.bit.bin'
assert Path('/sys/class/fpga_manager/fpga0/state').read_text().strip()=='operating'
p=subprocess.run(['xmutil','listapps'],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=15)
assert p.returncode==0
active=[x.split()[0] for x in p.stdout.splitlines() if len(x.split())==6 and x.split()[-1].rstrip(',')=='0']
assert active==['kv260-benchmark-b4096']
old=Path(sys.argv[1]);new=Path(sys.argv[2]);want=sys.argv[3];size=int(sys.argv[4])
assert old.is_file() and old.stat().st_size==size and hashlib.sha256(old.read_bytes()).hexdigest()==want
new.parent.mkdir(exist_ok=False)
os.link(old,new)
assert new.stat().st_size==size and hashlib.sha256(new.read_bytes()).hexdigest()==want
print(json.dumps({'reused_archive_verified':True,'sha256':want,'bytes':size,'destination':str(new),
 'boot_id':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),'mmio_accessed':False,'pl_changed':False}))
'''
(out/'remote.py').write_text(source)
spec=importlib.util.spec_from_file_location('reviewed_uart','/home/ghmd/kv260-dfx-state-boardtest-20261004/scripts/uart_phase.py')
module=importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
status={'phase':'uart-restage','complete':False,'evidence':str(out),'source':previous['source'],
 'destination':dest,'bytes':previous['bytes'],'sha256':previous['sha256'],
 'reused_board_archive':previous['destination'],'transport_method':'hash-verified-board-hardlink',
 'pl_loaded':False,'start_sent':False}
try:
 with (out/'uart.raw').open('wb') as raw:
  uart=module.UART(raw)
  try:
   uart.connect()
   payload=base64.b64encode(gzip.compress(source.encode(),mtime=0)).decode()
   code='import base64,gzip;exec(gzip.decompress(base64.b64decode('+repr(payload)+')))'
   cmd='python3 -B -c '+shlex.quote(code)
   for arg in (previous['destination'],dest,previous['sha256'],previous['bytes']):cmd+=' '+shlex.quote(str(arg))
   rc,data,digest=uart.command(cmd,'SQUARE_RESTAGE',45)
   (out/'result.output').write_bytes(data)
   status.update(rc=rc,result_sha256=digest)
   if rc:raise RuntimeError(data.decode(errors='replace'))
   status.update(result=json.loads(data),complete=True)
  finally:status['console_echo_restored']=uart.close()
finally:
 (out/'status.json').write_text(json.dumps(status,indent=2)+'\n')
 if status['complete']:(ROOT/'CURRENT_BOARD_STAGE.json').write_text(json.dumps(status,indent=2)+'\n')
 print(json.dumps(status,indent=2))
