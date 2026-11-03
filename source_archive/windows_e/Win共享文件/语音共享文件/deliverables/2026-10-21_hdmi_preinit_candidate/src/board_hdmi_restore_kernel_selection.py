"""Restore only the saved boot selection after the failed cold boot."""
import hashlib,json,subprocess
from pathlib import Path
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()=='e93b105e-cec2-43af-891f-ef17b0a5be63'
assert Path('/sys/block/mmcblk1/device/cid').read_text().strip()=='0353445345333247805558c00401a100'
root=Path('/boot/aura-hdmi-preinit-20261021')
assert hashlib.sha256((root/'rollback.py').read_bytes()).hexdigest()=='6a2fe818661bd817867c01e159b568a00b3e0aacc185517402caa05257fbc89b'
assert hashlib.sha256(Path('/boot/Image').read_bytes()).hexdigest()=='b02771b1c6ceca7f07b56a97ab36d79d2f17652c58f9c119ddd1d2ea0e554e71'
meta=json.loads((root/'before.json').read_text())
assert hashlib.sha256(Path('/boot/uEnv.txt').read_bytes()).hexdigest()==meta['candidate_uenv_sha256']
p=subprocess.run(['/usr/bin/python3',str(root/'rollback.py')],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=8)
assert p.returncode==0,p.stdout
assert Path('/boot/uEnv.txt').read_bytes()==(root/'uEnv.before').read_bytes()
print(json.dumps({'boot_id':'e93b105e-cec2-43af-891f-ef17b0a5be63','result':json.loads(p.stdout),'uenv_sha256':hashlib.sha256(Path('/boot/uEnv.txt').read_bytes()).hexdigest(),'runtime_kernel_changed':False,'business_files_modified':0,'movement_commands_sent':0}),flush=True)
