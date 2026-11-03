import os,json,hashlib,subprocess,re
from pathlib import Path
WORK=Path('/home/root/kv260-zocl-repair-20261003T005805Z')
ORIGINAL_SHA='215fe760dafb6766545e308d8bc207c31712154fe5a8ed08342a101a5482a98d'
PARAMS={'enable_xgq_ert': '1'}
def digest(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def active_packages():
 text=subprocess.check_output(['dfx-mgr-client','-listPackage'],text=True)
 result=[]
 for line in text.splitlines():
  fields=line.split()
  if fields and re.fullmatch(r'-?\d+,?',fields[-1]):
   slot=int(fields[-1].rstrip(','))
   if slot!=-1: result.append((fields[0],slot))
 return result
def guard(expected,app):
 assert os.geteuid()==0 and os.uname().release=='5.15.36-xilinx-v2022.2','Unexpected root/kernel'
 assert Path('/sys/class/block/mmcblk1/device/cid').read_text().strip()=='0353445345333247805558c00401a100','Wrong test card'
 dev=os.stat('/').st_dev
 assert Path('/sys/dev/block/%d:%d'%(os.major(dev),os.minor(dev))).resolve().name=='mmcblk1p2','Wrong root partition'
 assert digest('/lib/modules/5.15.36-xilinx-v2022.2/extra/zocl.ko')==ORIGINAL_SHA,'Original module changed'
 if (WORK/'baseline/state.json').exists():
  saved=json.loads((WORK/'baseline/state.json').read_text())
  assert saved['boot_id']==Path('/proc/sys/kernel/random/boot_id').read_text().strip(),'Boot changed'
 m=Path('/sys/module/zocl')
 if expected is None: assert not m.exists(),'ZOCL unexpectedly loaded'
 else:
  assert (m/'srcversion').read_text().strip()==expected,'Wrong loaded module'
  assert int((m/'refcnt').read_text())==0 and not list((m/'holders').iterdir()),'ZOCL busy'
  assert {p.name:p.read_text().strip() for p in (m/'parameters').iterdir()}==PARAMS,'Module parameters changed'
 nodes={'/dev/dri/card1','/dev/dri/renderD128'}
 for p in Path('/sys/class/drm').iterdir():
  module=p/'device/driver/module'
  if module.exists() and str(module.resolve())=='/sys/module/zocl': nodes.add('/dev/dri/'+p.name)
 for proc in Path('/proc').iterdir():
  if not proc.name.isdigit(): continue
  try:
   for fd in (proc/'fd').iterdir():
    try: target=os.readlink(fd).split(' (deleted)')[0]
    except OSError: continue
    assert target not in nodes,'DRM client still open: PID '+proc.name
  except (FileNotFoundError,PermissionError): continue
 wanted=[] if app is None else [(app,0)]
 assert active_packages()==wanted,'Unexpected active packages'
def snapshot(label):
 print(label+'_UPTIME '+Path('/proc/uptime').read_text().strip(),flush=True)
 print(label+'_ACTIVE '+json.dumps(active_packages()),flush=True)
 print(label+'_DMESG_BEGIN',flush=True)
 subprocess.run(['dmesg'],check=True)
 print(label+'_DMESG_END',flush=True)

WORK=Path('/home/root/kv260-dfx-manager-repair-20261003T042210Z')
INPUTS={'/usr/bin/dfx-mgrd': 'bdbd8ee09b3f767a53bd5111240c9ade3bb19b1da83d73bd06785ae86260e9a2', '/usr/bin/dfx-mgr-client': 'a37d8449c3362a509d459f9e57aa3711314602369354f7d98ca60c3e51607ad7', '/usr/lib/libdfx.so.1.0': '1acb6c9ac1f27e0ea769dc231f32db5565f6ca02a53be00e969fc48c038d290f', '/lib/libc.so.6': '2d68f8d6162252fb0efc481b59a508c16c1c6c3be3d683f8fce269a4af0cc34a', '/lib/libpthread.so.0': '87b3d947da289b44c1925511e2666ffdd9860cb9cd1730a0f0d928a196a52af4', '/lib/ld-linux-aarch64.so.1': 'af37b88e079a49854baef51db64bd478936ebdf6bb51e85cb759358ae4ccf0c2', '/lib/modules/5.15.36-xilinx-v2022.2/extra/zocl.ko': '215fe760dafb6766545e308d8bc207c31712154fe5a8ed08342a101a5482a98d', '/etc/vart.conf': 'd669edeae713e9e0b5ffdf9d050b11c11f1fc2add68fa1dc8b25483e8d7c59ba', '/etc/dfx-mgrd/daemon.conf': 'a517938929fe978aa2975de76cf360a426d2fc5444fbd6d728a96dfa93603a08', '/lib/firmware/xilinx/kv260-benchmark-b4096/kv260-benchmark-b4096.bit.bin': '7d12c877e0fde40a243d2350b1a2227f565788bf9e2dcae4439d07f213d40a3f', '/lib/firmware/xilinx/kv260-benchmark-b4096/kv260-benchmark-b4096.dtbo': '36338937904e5ec988566d7341f6504edba34c01bd7e2e3f2025ab0069337e35', '/lib/firmware/xilinx/kv260-benchmark-b4096/shell.json': '2967ccbc1f75c8d4accd1b6fecc11b16a32a5d7992e56c6eebceb99a3410f777', '/lib/firmware/xilinx/kv260-benchmark-b4096/kv260-benchmark-b4096.xclbin': 'fc3abb934eec544e49a17c484336cf177258f475522cefc994ec458b726f69ac', '/usr/share/vitis_ai_library/models/resnet18/resnet18.xmodel': '4d4d669c84b6d5aa6f731b389ebcf0f51fb1449752cf5fa4a4beddd496c3c0ef', '/usr/share/vitis_ai_library/models/resnet18/resnet18.prototxt': '691c393b15ae87976060a125067534334bd034c3a5193a96f6f5db3f4da3729c', '/home/root/kv260-test-20261001/pytorch-resnet-dog.jpg': 'f3f87bb8ab3c26c7ecfd3ac60421d7f32b0503d1d6c5baf8bac42ed93d86351a', '/home/root/kv260-test-20261001/samoyed.list': 'bf02d74370fbfdd8d008c7916109a14be3a5b33bd6057522fbb14e95ac2e9caa', '/home/root/kv260-test-20261001/baseline-backup/baseline-files.tar.gz': '964c04afac0d7de7e36b78d6bdd87f5f4a656bb47b3b7e1a7169510f5dfaa371', '/home/root/Vitis-AI/examples/vai_library/samples/classification/test_jpeg_classification': '322dd07736f409cba02416782475c0dc2b5951435ddbb6d0671d3cda8fac0c0e', '/home/root/Vitis-AI/examples/vai_library/samples/classification/test_performance_classification': 'b9f52e4fd21d6526a8ac1e73b6e839b28308368451c4bb30e845a9f96343f1b4', '/etc/dfx-mgrd/default_firmware': '7e78c8b095e77ec1fdfa5cdd8b26192d8feb849405b55a50e8fe6562a35f18b2', '/lib/systemd/system/dfx-mgr.service': 'a5ba3c45b4bddf9a818d7aa7b34507cc0321296d90e51288f5d930e2293866b6'}
CANDIDATE_SHA='db9c25f09f1178177884b1114c57f32c076f1e7f9cdd0d12b7a896039038a46c'
OVERRIDE=Path('/run/systemd/system/dfx-mgr.service.d/kv260-watchtest-20261003T042210Z.conf')
def files_guard():
 for path,expected in INPUTS.items(): assert digest(path)==expected,'Original file changed: '+path
def gate(driver,app):
 guard(driver,app)
 files_guard()
 if app is not None:
  assert Path('/sys/class/fpga_manager/fpga0/state').read_text().strip()=='operating'
  assert Path('/proc/device-tree/fpga-full/firmware-name').read_bytes().rstrip(b'\0').decode()==app+'.bit.bin'
def manager_pid():
 return int(subprocess.check_output(['systemctl','show','dfx-mgr.service','--property=MainPID','--value'],text=True))
def manager_guard(candidate):
 pid=manager_pid();assert pid>0 and subprocess.check_output(['systemctl','is-active','dfx-mgr.service'],text=True).strip()=='active'
 path=str(WORK/'candidate-stage/dfx-mgrd') if candidate else '/usr/bin/dfx-mgrd'
 assert os.readlink('/proc/%d/exe'%pid)==path,'Unexpected manager executable'
 assert digest(path)==(CANDIDATE_SHA if candidate else INPUTS['/usr/bin/dfx-mgrd'])
 if candidate:assert not manager_errors(),'Candidate manager error; inspect full log'
def manager_errors():
 p=WORK/'candidate-manager.log'
 return [s for s in p.read_text(errors='replace').splitlines() if 'ERROR:' in s] if p.exists() else []
def watches():
 total=0
 for p in (Path('/proc')/str(manager_pid())/'fdinfo').iterdir():
  try:total+=p.read_text().count('inotify wd:')
  except FileNotFoundError:pass
 return total
def wait_manager(candidate):
 import socket,time
 for unused in range(100):
  pid=manager_pid()
  if pid>0:
   s=socket.socket(socket.AF_UNIX,socket.SOCK_STREAM)
   ret=s.connect_ex('/tmp/dfx-mgrd.socket');s.close()
   if ret==0:manager_guard(candidate);return
  time.sleep(.1)
 raise RuntimeError('Manager startup did not become ready')
