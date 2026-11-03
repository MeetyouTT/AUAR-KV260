
import json,os,subprocess,shutil
from pathlib import Path
assert os.uname().machine=='aarch64'
assert Path('/sys/block/mmcblk1/device/cid').read_text().strip()=='0353445345333247805558c00401a100'
def run(args):
 try:
  p=subprocess.run(args,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=12)
  return {'rc':p.returncode,'output':p.stdout[:16000]}
 except Exception as e:return {'error':str(e)}
videos={str(p):{'name':(p/'name').read_text().strip(),'device':str((p/'device').resolve())} for p in Path('/sys/class/video4linux').glob('video*')}
commands=[['cat', '/sys/kernel/debug/gpio'], ['sh', '-c', 'ls -l /sys/bus/i2c/drivers/usb5744/; ls -l /sys/bus/platform/drivers/xhci-hcd/'], ['sh', '-c', "dmesg | grep -Ei 'usb|hub|regulator|over.current|gpio|fpga' | tail -100"], ['sh', '-c', 'cat /proc/uptime; lsusb -t'], ['python3', '-c', "from pathlib import Path;import json;root=Path('/sys/firmware/devicetree/base');out={};\nfor p in root.rglob('compatible'):\n b=p.read_bytes();\n if b'usb5744' in b or b'usb-hub' in b or b'usb2734' in b:\n  out[str(p.parent)]={x.name:x.read_bytes().hex() for x in p.parent.iterdir() if x.is_file()}\nprint(json.dumps(out))"]]
for p in sorted(Path('/dev').glob('video*')):commands.append(['v4l2-ctl','-d',str(p),'--list-formats-ext'])
print(json.dumps({'boot_id':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),'video_devices':videos,'commands':{' '.join(a):run(a) for a in commands},'tools':{x:shutil.which(x) for x in ['gst-launch-1.0','gst-inspect-1.0','v4l2-ctl','ffplay','xdputil','python3']},'models':{str(p):[x.name for x in p.iterdir()] if p.exists() else [] for p in [Path('/usr/share/vitis_ai_library/models'),Path('/usr/share/vitis_ai_library/samples'),Path('/home/root/aura')]}}))
