import json,hashlib
from pathlib import Path
expected={'/usr/bin/dfx-mgrd': 'bdbd8ee09b3f767a53bd5111240c9ade3bb19b1da83d73bd06785ae86260e9a2', '/usr/bin/dfx-mgr-client': 'a37d8449c3362a509d459f9e57aa3711314602369354f7d98ca60c3e51607ad7', '/usr/lib/libdfx.so.1.0': '1acb6c9ac1f27e0ea769dc231f32db5565f6ca02a53be00e969fc48c038d290f', '/lib/libc.so.6': '2d68f8d6162252fb0efc481b59a508c16c1c6c3be3d683f8fce269a4af0cc34a', '/lib/libpthread.so.0': '87b3d947da289b44c1925511e2666ffdd9860cb9cd1730a0f0d928a196a52af4', '/lib/ld-linux-aarch64.so.1': 'af37b88e079a49854baef51db64bd478936ebdf6bb51e85cb759358ae4ccf0c2', '/lib/modules/5.15.36-xilinx-v2022.2/extra/zocl.ko': '215fe760dafb6766545e308d8bc207c31712154fe5a8ed08342a101a5482a98d', '/etc/vart.conf': 'd669edeae713e9e0b5ffdf9d050b11c11f1fc2add68fa1dc8b25483e8d7c59ba', '/etc/dfx-mgrd/daemon.conf': 'a517938929fe978aa2975de76cf360a426d2fc5444fbd6d728a96dfa93603a08'}
actual={p:hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in expected}
print(json.dumps(actual,indent=2),flush=True)
assert actual==expected,'Baseline file hash differs'
