import os,json,hashlib,subprocess,shutil
from pathlib import Path
WORK=Path('/home/root/kv260-runtime-live-20261003T085031Z')
assert os.geteuid()==0 and os.uname().release=='5.15.36-xilinx-v2022.2'
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()=='64083069-98b7-409b-a455-b7b3b7158745'
assert Path('/sys/class/block/mmcblk1/device/cid').read_text().strip()=='0353445345333247805558c00401a100'
assert Path('/sys/module/zocl/srcversion').read_text().strip()=='0991D1B457855C8987936E6'
assert Path('/sys/module/zocl/refcnt').read_text().strip()=='0'
assert shutil.disk_usage('/home/root').free>1073741824
expected={'/home/root/Vitis-AI/examples/vai_library/samples/classification/test_jpeg_classification': '322dd07736f409cba02416782475c0dc2b5951435ddbb6d0671d3cda8fac0c0e', '/home/root/Vitis-AI/examples/vai_library/samples/classification/test_performance_classification': 'b9f52e4fd21d6526a8ac1e73b6e839b28308368451c4bb30e845a9f96343f1b4', '/lib/firmware/xilinx/kv260-benchmark-b4096-m3/kv260-benchmark-b4096-m3.bit.bin': 'a48a25265d280f268300f627e6408ec56707a70d4deebe46e358500cf17b2650', '/lib/firmware/xilinx/kv260-benchmark-b4096-m3/kv260-benchmark-b4096-m3.dtbo': '51ce617967e0c0657bcc2629f1a0a8efa1e4bad3f3bc8f0b1931aacb5bf91937', '/lib/firmware/xilinx/kv260-benchmark-b4096-m3/kv260-benchmark-b4096-m3.xclbin': '875ca912d87b2c993716f4c353265a9cf403b0c9890442610e64291787caafc3', '/lib/firmware/xilinx/kv260-benchmark-b4096-m3/shell.json': '802dbc8b3f118313a5a74df46f56dc550a61b687dfd484fc6a8fd5ac7895c344', '/etc/dfx-mgrd/default_firmware': '7e78c8b095e77ec1fdfa5cdd8b26192d8feb849405b55a50e8fe6562a35f18b2', '/lib/systemd/system/dfx-mgr.service': 'a5ba3c45b4bddf9a818d7aa7b34507cc0321296d90e51288f5d930e2293866b6'}
actual={}
for path,sha in expected.items():
 p=Path(path);data=p.read_bytes();assert hashlib.sha256(data).hexdigest()==sha,path
 dest=WORK/'baseline/files'/path.lstrip('/');dest.parent.mkdir(parents=True,exist_ok=True)
 assert not dest.exists();shutil.copy2(path,str(dest))
 assert hashlib.sha256(dest.read_bytes()).hexdigest()==sha
 actual[path]={'bytes':len(data),'sha256':sha,'backup':str(dest)}
print('BACKUP_FILES '+json.dumps(actual),flush=True)
