#!/usr/bin/env python3
"""Read board identity/loading status over UART without MMIO or mutations."""
import base64
import datetime
import gzip
import importlib.util
import json
from pathlib import Path
import shlex

ROOT = Path(__file__).resolve().parents[1]
tag = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')
out = ROOT / 'evidence' / (tag + '-uart-state')
out.mkdir(exist_ok=False)
source = r'''
import json,os,subprocess
from pathlib import Path
assert os.uname().machine=='aarch64' and os.geteuid()==0
assert Path('/sys/block/mmcblk1/device/cid').read_text().strip()=='0353445345333247805558c00401a100'
def read(path):
 p=Path(path)
 return p.read_bytes().rstrip(b'\x00\n').decode() if p.exists() else None
def run(argv):
 p=subprocess.run(argv,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=15)
 return {'rc':p.returncode,'output':p.stdout}
print(json.dumps({'boot_id':read('/proc/sys/kernel/random/boot_id'),
 'fpga_state':read('/sys/class/fpga_manager/fpga0/state'),
 'firmware':read('/proc/device-tree/fpga-full/firmware-name'),
 'all_firmware_names':{str(p):read(str(p)) for p in Path('/proc/device-tree').rglob('firmware-name')},
 'apps':run(['xmutil','listapps']),'manager':run(['systemctl','is-active','dfx-mgr']),
 'uptime':read('/proc/uptime'),
 'watchdog':{str(p):read(str(p)) for p in Path('/sys/class/watchdog').glob('watchdog*/*')
             if p.name in ('identity','state','status','bootstatus','timeout','nowayout')},
 'pstore':{str(p):p.read_text(errors='replace')[:12000] for p in Path('/sys/fs/pstore').glob('*') if p.is_file()},
 'journal_boots':run(['journalctl','--list-boots','--no-pager']),
 'previous_kernel_tail':run(['journalctl','-b','-1','-k','-n','35','--no-pager']),
 'mmio_accessed':False,'mutations':False}))
'''
(out / 'remote.py').write_text(source)
transport = Path('/home/ghmd/kv260-dfx-state-boardtest-20261004/scripts/uart_phase.py')
spec = importlib.util.spec_from_file_location('reviewed_uart', transport)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
status = {'phase':'uart-state','complete':False,'evidence':str(out),'mmio_accessed':False,'board_mutated':False}
try:
 with (out / 'uart.raw').open('wb') as raw:
  uart=module.UART(raw)
  try:
   uart.connect()
   payload=base64.b64encode(gzip.compress(source.encode(),mtime=0)).decode()
   code='import base64,gzip;exec(gzip.decompress(base64.b64decode('+repr(payload)+')))'
   rc,data,digest=uart.command('python3 -B -c '+shlex.quote(code),'SQUARE_STATE',45)
   (out/'result.output').write_bytes(data)
   status.update(rc=rc,result_sha256=digest)
   if rc:raise RuntimeError(data.decode(errors='replace'))
   status.update(result=json.loads(data),complete=True)
  finally:status['console_echo_restored']=uart.close()
finally:
 (out/'status.json').write_text(json.dumps(status,indent=2)+'\n')
 (ROOT/'CURRENT_BOARD_STATE.json').write_text(json.dumps(status,indent=2)+'\n')
 print(json.dumps(status,indent=2))
