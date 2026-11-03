import hashlib,json,subprocess,time
from pathlib import Path
source=Path('/home/root/aura-adaptation-20261006/identity_dpu_engineering_20261018/helpers/18c189ef3dca8728/source.py')
assert hashlib.sha256(source.read_bytes()).hexdigest()=='18c189ef3dca872826601e84aef6c0b63b313c8aca9f2f8d9884df3d99f31136'
assert hashlib.sha256(Path('/etc/systemd/system/aura-camera-ui.service').read_bytes()).hexdigest()=='84116d8faf6f4d3972f5f2eac35f8c98cf8ecbe51752a8f78d803aa8a7cdd75c'
start=time.monotonic();r=subprocess.run(['journalctl','-k','-n','0','--show-cursor','--no-pager'],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=8)
assert r.returncode==0 and b'-- cursor: ' in r.stdout
latency=time.monotonic()-start
root=Path('/home/root/aura-dpu-vision-20261021/gil-long-launches/18c189ef3dca8728')
old=root/'launch-result.json';v=json.loads(old.read_text());assert 'TimeoutExpired' in v.get('error','')
archive=root/'launch-result-before-r2.json';assert not archive.exists();old.rename(archive)
unit='aura-gil-1ms-600-18c189ef3dca8728-r2'
r=subprocess.run(['systemd-run','--unit='+unit,'--property=RuntimeMaxSec=900','--setenv=AURA_GIL_LONG_RUN=1','/usr/bin/python3','-B',str(source)],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=8)
assert r.returncode==0,r.stdout.decode(errors='replace')
print(json.dumps({'started':True,'unit':unit,'journal_cursor_query_seconds':latency,'prior_timeout_preserved':True}))
