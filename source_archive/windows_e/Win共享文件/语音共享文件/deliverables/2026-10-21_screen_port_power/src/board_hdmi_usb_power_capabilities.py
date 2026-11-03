"""Read only the identified hub descriptors and display startup evidence."""
import json,re,shutil,subprocess
from pathlib import Path
v={'boot_id':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),'usb_control_writes':0,'mode_changes':0}
v['uhubctl']=shutil.which('uhubctl')
v['libusb_files']=[str(p) for parent in [Path('/usr/lib'),Path('/lib')] for p in parent.glob('libusb-1.0.so*')]
v['hubs']=[]
for name in ['1-1','2-1']:
 p=Path('/sys/bus/usb/devices')/name
 if not p.exists():continue
 ids={k:(p/k).read_text().strip() for k in ['idVendor','idProduct','busnum','devnum','bNbrInterfaces'] if (p/k).exists()}
 assert ids['idVendor']=='0424' and ids['idProduct'] in ['2744','5744']
 r=subprocess.run(['lsusb','-v','-s',ids['busnum']+':'+ids['devnum']],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=5)
 lines=r.stdout.splitlines();keep=[];inside=False
 for s in lines:
  if re.search(r'Hub Descriptor|Hub Port Status|wHubCharacteristic|bNbrPorts|bPwrOn2PwrGood|power switching|power switch|Port [0-9]+:|PortPwrCtrlMask',s,re.I):keep.append(s)
 v['hubs'].append({'bus_path':name,'ids':ids,'descriptor_filtered':keep,'lsusb_rc':r.returncode})
v['topology']=subprocess.check_output(['lsusb','-t'],text=True,timeout=5)
v['initial_modes']=[s for s in Path('/var/log/Xorg.0.log').read_text().splitlines() if 'using initial mode' in s or 'AURA-HDMI' in s]
v['fbdev_emulation']=Path('/sys/module/drm_kms_helper/parameters/fbdev_emulation').read_text().strip()
v['framebuffers']=[p.name for p in Path('/sys/class/graphics').glob('fb[0-9]*')]
print(json.dumps(v),flush=True)
