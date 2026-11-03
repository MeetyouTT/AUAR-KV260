import hashlib
from pathlib import Path
p=Path('/home/root/kv260-m3-boardtest-20261003T021012Z/baseline/guard_reference.py')
G=p.read_bytes()
assert hashlib.sha256(G).hexdigest()=='99c1fc5c842a026c05531eb637080717e44aaa199220d8ab942fbfe430814a6e','Guard source changed'
exec(compile(G,str(p),'exec'))
WORK=Path('/home/root/kv260-m3-boardtest-20261003T021012Z')
def baseline_hashes():
 p=WORK/'baseline/runtime-hashes.json'
 assert digest(p)=='89be552ca73fbc1d8cf4ff94dd1dd6f2f6b8dc7f5d25ab151ada76a733853c0e','Saved manifest changed'
 for path,expected in json.loads(p.read_text()).items():
  assert digest(path)==expected,'Baseline file changed: '+path
def gate(expected,app):
 guard(expected,app)
 baseline_hashes()
 if app is not None:
  assert Path('/sys/class/fpga_manager/fpga0/state').read_text().strip()=='operating'
  assert Path('/proc/device-tree/fpga-full/firmware-name').read_bytes().rstrip(b'\0').decode()==app+'.bit.bin'
def capture(label):
 snapshot(label)
 print(label+'_MANAGER_JOURNAL_BEGIN',flush=True)
 r=subprocess.run(['journalctl','-u','dfx-mgrd','--no-pager','-n','200','-o','short-monotonic'])
 print(label+'_MANAGER_JOURNAL_RC '+str(r.returncode),flush=True)
 print(label+'_MANAGER_JOURNAL_END',flush=True)
gate('0991D1B457855C8987936E6','kv260-benchmark-b4096')
subprocess.run('python3 -B -c \'import os,json\nfrom pathlib import Path\nroot_dev=os.stat(\'"\'"\'/\'"\'"\').st_dev\ndrm=[]\nfor p in sorted(Path(\'"\'"\'/sys/class/drm\'"\'"\').iterdir()):\n if not (p.name.startswith(\'"\'"\'card\'"\'"\') or p.name.startswith(\'"\'"\'render\'"\'"\')) or not (p/\'"\'"\'device\'"\'"\').exists(): continue\n dev=p/\'"\'"\'device\'"\'"\'; driver=dev/\'"\'"\'driver\'"\'"\'\n drm.append({\'"\'"\'name\'"\'"\':p.name,\'"\'"\'device\'"\'"\':str(dev.resolve()),\'"\'"\'driver\'"\'"\':str(driver.resolve()) if driver.exists() else None,\'"\'"\'module\'"\'"\':str((driver/\'"\'"\'module\'"\'"\').resolve()) if (driver/\'"\'"\'module\'"\'"\').exists() else None})\nmodule=Path(\'"\'"\'/sys/module/zocl\'"\'"\')\nparams={p.name:p.read_text().strip() for p in (module/\'"\'"\'parameters\'"\'"\').iterdir()}\nfirmware=Path(\'"\'"\'/proc/device-tree/fpga-full/firmware-name\'"\'"\')\nprint(json.dumps({\'"\'"\'uptime\'"\'"\':Path(\'"\'"\'/proc/uptime\'"\'"\').read_text().strip(),\'"\'"\'root_device\'"\'"\':Path(\'"\'"\'/sys/dev/block/%d:%d\'"\'"\'%(os.major(root_dev),os.minor(root_dev))).resolve().name,\'"\'"\'drm\'"\'"\':drm,\'"\'"\'zocl_parameters\'"\'"\':params,\'"\'"\'loaded_srcversion\'"\'"\':(module/\'"\'"\'srcversion\'"\'"\').read_text().strip(),\'"\'"\'fpga_state\'"\'"\':Path(\'"\'"\'/sys/class/fpga_manager/fpga0/state\'"\'"\').read_text().strip(),\'"\'"\'firmware_name\'"\'"\':firmware.read_bytes().rstrip(b\'"\'"\'\\0\'"\'"\').decode(),\'"\'"\'vart_conf\'"\'"\':Path(\'"\'"\'/etc/vart.conf\'"\'"\').read_text()},indent=2))\n\'',shell=True,check=True)
