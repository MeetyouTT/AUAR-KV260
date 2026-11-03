#!/usr/bin/env python3
import base64,datetime,gzip,importlib.util,json,shlex
from pathlib import Path
root=Path(__file__).resolve().parent
out=root/'evidence'/datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ-display-wake');out.mkdir(parents=True)
source=r'''
import subprocess,json
from pathlib import Path
assert Path('/sys/block/mmcblk1/device/cid').read_text().strip()=='0353445345333247805558c00401a100'
def run(a):
 p=subprocess.run(a,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=15)
 return {'rc':p.returncode,'output':p.stdout}
r={}
r['wake']=run(['xset','-display',':0','dpms','force','on'])
r['display']=run(['xrandr','--display',':0','--verbose'])
text=r['display']['output']
if r['display']['rc']==0 and '1024x600' in text:
 r['native_mode']=run(['xrandr','--display',':0','--output','DP-1','--mode','1024x600'])
r['after']=run(['xrandr','--display',':0','--current'])
r['power']=run(['xset','-display',':0','q'])
print(json.dumps(r))
'''
(out/'remote.py').write_text(source)
spec=importlib.util.spec_from_file_location('uart','/home/ghmd/kv260-dfx-state-boardtest-20261004/scripts/uart_phase.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
with (out/'uart.raw').open('wb') as raw:
 u=m.UART(raw)
 try:
  u.connect();payload=base64.b64encode(gzip.compress(source.encode(),mtime=0)).decode();code='import base64,gzip;exec(gzip.decompress(base64.b64decode('+repr(payload)+')))'
  rc,data,h=u.command('python3 -B -c '+shlex.quote(code),'DISPLAY_WAKE',55)
  (out/'result.json').write_bytes(data);print(data.decode())
  if rc:raise RuntimeError('Display wake failed')
 finally:restored=u.close()
(root/'CURRENT_DISPLAY.json').write_text(json.dumps({'evidence':str(out),'rc':rc,'sha256':h,'console_echo_restored':restored},indent=2)+'\n')
