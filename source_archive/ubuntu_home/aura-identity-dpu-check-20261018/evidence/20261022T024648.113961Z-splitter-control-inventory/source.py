"""Inventory exposed I2C/GPIO controls without scanning buses or writing hardware."""
import glob,json,os,subprocess
from pathlib import Path
boot=Path('/proc/sys/kernel/random/boot_id').read_text().strip()
assert Path('/sys/block/mmcblk1/device/cid').read_text().strip()=='0353445345333247805558c00401a100'
def read(p):
 try:return Path(p).read_text(errors='replace').strip()
 except Exception:return None
def run(args):
 try:
  p=subprocess.run(args,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=5)
  return {'rc':p.returncode,'text':p.stdout[:5000]}
 except Exception as e:return {'error':str(e)}
i2c=[]
for p in sorted(glob.glob('/sys/bus/i2c/devices/*-*')):
 q=Path(p)
 if not re_fullmatch_i2c(q.name):continue
 i2c.append({'device':q.name,'name':read(q/'name'),'modalias':read(q/'modalias'),'compatible':read(q/'of_node/compatible'),'driver':str((q/'driver').resolve()) if (q/'driver').exists() else None})
gpio=[]
for p in sorted(glob.glob('/sys/bus/gpio/devices/gpiochip*')):
 q=Path(p);gpio.append({'device':q.name,'label':read(q/'label'),'base':read(q/'base'),'ngpio':read(q/'ngpio')})
dts=[]
for p in sorted(glob.glob('/proc/device-tree/**/i2c@*',recursive=True)):
 if p.count('/')>8:continue
 q=Path(p); dts.append({'node':p,'compatible':read(q/'compatible'),'status':read(q/'status'),'children':[c.name for c in q.iterdir() if '@' in c.name]})
print(json.dumps({'boot_id':boot,'board_model':read('/proc/device-tree/model'),'root_compatible':read('/proc/device-tree/compatible'),'i2c_adapters':run(['/usr/sbin/i2cdetect','-l']) if Path('/usr/sbin/i2cdetect').exists() else run(['/sbin/i2cdetect','-l']),'i2c_clients':i2c,'device_tree_i2c_nodes':dts,'gpio_chips':gpio,'gpioinfo':run(['/usr/bin/gpioinfo']) if Path('/usr/bin/gpioinfo').exists() else run(['/bin/gpioinfo']) if Path('/bin/gpioinfo').exists() else {'unavailable':True},'commands_that_scan_or_write':0,'i2c_transactions_to_splitter':0,'gpio_writes':0},indent=2),flush=True)
def re_fullmatch_i2c(name):
 import re
 return bool(re.fullmatch(r'\d+-[0-9a-fA-F]{4}',name))
