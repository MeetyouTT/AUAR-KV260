import os,json,hashlib,subprocess,shutil
from pathlib import Path
WORK=Path('/home/root/kv260-runtime-live-20261003T085031Z')
assert os.geteuid()==0 and os.uname().release=='5.15.36-xilinx-v2022.2'
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()=='64083069-98b7-409b-a455-b7b3b7158745'
assert Path('/sys/class/block/mmcblk1/device/cid').read_text().strip()=='0353445345333247805558c00401a100'
assert Path('/sys/module/zocl/srcversion').read_text().strip()=='0991D1B457855C8987936E6'
assert Path('/sys/module/zocl/refcnt').read_text().strip()=='0'
assert shutil.disk_usage('/home/root').free>1073741824
expected={'/usr/bin/dfx-mgrd': 'bdbd8ee09b3f767a53bd5111240c9ade3bb19b1da83d73bd06785ae86260e9a2', '/usr/bin/dfx-mgr-client': 'a37d8449c3362a509d459f9e57aa3711314602369354f7d98ca60c3e51607ad7', '/usr/lib/libdfx.so.1.0': '1acb6c9ac1f27e0ea769dc231f32db5565f6ca02a53be00e969fc48c038d290f', '/lib/libc.so.6': '2d68f8d6162252fb0efc481b59a508c16c1c6c3be3d683f8fce269a4af0cc34a', '/lib/libpthread.so.0': '87b3d947da289b44c1925511e2666ffdd9860cb9cd1730a0f0d928a196a52af4', '/lib/ld-linux-aarch64.so.1': 'af37b88e079a49854baef51db64bd478936ebdf6bb51e85cb759358ae4ccf0c2', '/lib/modules/5.15.36-xilinx-v2022.2/extra/zocl.ko': '215fe760dafb6766545e308d8bc207c31712154fe5a8ed08342a101a5482a98d', '/etc/vart.conf': 'd669edeae713e9e0b5ffdf9d050b11c11f1fc2add68fa1dc8b25483e8d7c59ba', '/etc/dfx-mgrd/daemon.conf': 'a517938929fe978aa2975de76cf360a426d2fc5444fbd6d728a96dfa93603a08'}
actual={}
for path,sha in expected.items():
 p=Path(path);data=p.read_bytes();assert hashlib.sha256(data).hexdigest()==sha,path
 dest=WORK/'baseline/files'/path.lstrip('/');dest.parent.mkdir(parents=True,exist_ok=True)
 assert not dest.exists();shutil.copy2(path,str(dest))
 assert hashlib.sha256(dest.read_bytes()).hexdigest()==sha
 actual[path]={'bytes':len(data),'sha256':sha,'backup':str(dest)}
print('BACKUP_FILES '+json.dumps(actual),flush=True)
