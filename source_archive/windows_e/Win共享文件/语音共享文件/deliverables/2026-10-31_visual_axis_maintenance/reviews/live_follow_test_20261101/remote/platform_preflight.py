"""Read platform-loader availability and native recovery overrides before stopping anything."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

ops=Path('/home/root/aura-native-live-20261024/ops/be72669aa53de735')
operator=ops/'pan-face-edge-v5/native-operator-v1'
files=[]
for path in (operator/'settings.json',operator/'identity_recovery.py'):
    raw=path.read_bytes();assert len(raw)<100000
    files.append(dict(path=str(path),sha256=hashlib.sha256(raw).hexdigest(),content=raw.decode()))
xmutil=shutil.which('xmutil')
assert xmutil
p=subprocess.run([xmutil,'listapps'],capture_output=True,text=True,timeout=10)
assert len(p.stdout)<16000 and len(p.stderr)<4000
active=[]
for proc in Path('/proc').iterdir():
    if not proc.name.isdigit():continue
    try:
        maps=(proc/'maps').read_text()
        if 'libvart' not in maps and 'libaura_native_v2' not in maps:continue
        active.append(dict(pid=int(proc.name),cmdline=(proc/'cmdline').read_bytes().replace(b'\0',b' ').decode()[:1000],
            vart_loaded='libvart' in maps,native_loaded='libaura_native_v2' in maps))
    except (OSError,UnicodeError):continue
print(json.dumps(dict(xmutil=xmutil,listapps_returncode=p.returncode,listapps=p.stdout,
    listapps_error_present=bool(p.stderr),vart_conf=Path('/etc/vart.conf').read_text(),
    firmware=Path('/proc/device-tree/fpga-full/firmware-name').read_bytes().rstrip(b'\0').decode(),
    dpu_processes=active,files=files,services_changed=False)))
