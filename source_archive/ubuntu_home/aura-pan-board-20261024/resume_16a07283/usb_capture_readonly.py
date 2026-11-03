import json,subprocess,shutil
from pathlib import Path
out={'kernel':Path('/proc/sys/kernel/osrelease').read_text().strip(),'printk':Path('/proc/sys/kernel/printk').read_text().strip()}
for executable,args,key in [('lsusb',['-t'],'usb_tree'),('v4l2-ctl',['--device','/dev/video0','--get-fmt-video','--get-parm'],'video_format')]:
 if shutil.which(executable):
  p=subprocess.run([executable]+args,capture_output=True,text=True,timeout=4);out[key]={'returncode':p.returncode,'stdout':p.stdout[-4500:],'stderr':p.stderr[-300:]}
devices=[]
for p in Path('/sys/bus/usb/devices').glob('*'):
 if ':' in p.name:continue
 row={'path':p.name}
 for key in ('busnum','devnum','idVendor','idProduct','product','speed'):
  try:row[key]=(p/key).read_text().strip()
  except OSError:pass
 if 'idVendor' in row:devices.append(row)
out['usb_devices']=devices
ops=Path('/home/root/aura-native-live-20261024/ops/be72669aa53de735');meta=json.loads((ops/'meta.json').read_text());cfg=json.loads(Path(meta['candidate_config']).read_text())
out['camera_config']={k:v for k,v in cfg.items() if k in ('device','width','height','fps','input_format','camera','preview','capture','role','source','pipeline')}
print(json.dumps(out))
