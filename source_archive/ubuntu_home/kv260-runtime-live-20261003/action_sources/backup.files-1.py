import os,json,hashlib,subprocess,shutil
from pathlib import Path
WORK=Path('/home/root/kv260-runtime-live-20261003T082232Z')
assert os.geteuid()==0 and os.uname().release=='5.15.36-xilinx-v2022.2'
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()=='64083069-98b7-409b-a455-b7b3b7158745'
assert Path('/sys/class/block/mmcblk1/device/cid').read_text().strip()=='0353445345333247805558c00401a100'
assert Path('/sys/module/zocl/srcversion').read_text().strip()=='0991D1B457855C8987936E6'
assert Path('/sys/module/zocl/refcnt').read_text().strip()=='0'
assert shutil.disk_usage('/home/root').free>1073741824
expected={'/lib/firmware/xilinx/kv260-benchmark-b4096/kv260-benchmark-b4096.bit.bin': '7d12c877e0fde40a243d2350b1a2227f565788bf9e2dcae4439d07f213d40a3f', '/lib/firmware/xilinx/kv260-benchmark-b4096/kv260-benchmark-b4096.dtbo': '36338937904e5ec988566d7341f6504edba34c01bd7e2e3f2025ab0069337e35', '/lib/firmware/xilinx/kv260-benchmark-b4096/shell.json': '2967ccbc1f75c8d4accd1b6fecc11b16a32a5d7992e56c6eebceb99a3410f777', '/lib/firmware/xilinx/kv260-benchmark-b4096/kv260-benchmark-b4096.xclbin': 'fc3abb934eec544e49a17c484336cf177258f475522cefc994ec458b726f69ac', '/usr/share/vitis_ai_library/models/resnet18/resnet18.xmodel': '4d4d669c84b6d5aa6f731b389ebcf0f51fb1449752cf5fa4a4beddd496c3c0ef', '/usr/share/vitis_ai_library/models/resnet18/resnet18.prototxt': '691c393b15ae87976060a125067534334bd034c3a5193a96f6f5db3f4da3729c', '/home/root/kv260-test-20261001/pytorch-resnet-dog.jpg': 'f3f87bb8ab3c26c7ecfd3ac60421d7f32b0503d1d6c5baf8bac42ed93d86351a', '/home/root/kv260-test-20261001/samoyed.list': 'bf02d74370fbfdd8d008c7916109a14be3a5b33bd6057522fbb14e95ac2e9caa', '/home/root/kv260-test-20261001/baseline-backup/baseline-files.tar.gz': '964c04afac0d7de7e36b78d6bdd87f5f4a656bb47b3b7e1a7169510f5dfaa371'}
actual={}
for path,sha in expected.items():
 p=Path(path);data=p.read_bytes();assert hashlib.sha256(data).hexdigest()==sha,path
 dest=WORK/'baseline/files'/path.lstrip('/');dest.parent.mkdir(parents=True,exist_ok=True)
 assert not dest.exists();shutil.copy2(path,str(dest))
 assert hashlib.sha256(dest.read_bytes()).hexdigest()==sha
 actual[path]={'bytes':len(data),'sha256':sha,'backup':str(dest)}
print('BACKUP_FILES '+json.dumps(actual),flush=True)
