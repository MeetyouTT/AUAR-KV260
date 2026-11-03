import json,os,urllib.request
from pathlib import Path
root=Path('/sys/kernel/debug/usb/xhci/xhci-hcd.1.auto/devices');out={'slots':[p.name for p in root.iterdir()] if root.exists() else []}
out['slot4']={}
for n in ('04','4','004','slot04','slot4'):
 p=root/n
 if not p.exists():continue
 out['slot4']['directory']=str(p);out['slot4']['files']=[x.name for x in p.iterdir()]
 for f in p.iterdir():
  if f.is_file() and any(x in f.name for x in ('slot','name','info')):
   try:out['slot4'][f.name]=f.read_text()[:3000]
   except OSError:pass
pid=137376;p=Path('/proc')/str(pid)
if p.exists():
 args=(p/'cmdline').read_bytes().split(b'\0');out['pcm_worker']={'pid':pid,'python_scripts':[x.decode(errors='replace') for x in args if x.endswith(b'.py')],
  'code_argument_sha256':__import__('hashlib').sha256(args[2]).hexdigest() if len(args)>2 and args[1]==b'-c' else None,'cgroup':(p/'cgroup').read_text()}
for name in ('/proc/asound/card1/pcm0p/sub0/hw_params','/proc/asound/card1/stream0'):
 p=Path(name)
 if p.exists():out[name]=p.read_text()[:4500]
o=urllib.request.build_opener(urllib.request.ProxyHandler({}))
with o.open('http://127.0.0.1:8783/api/state',timeout=3) as f:u=json.load(f)
out['product_activity']={k:u.get(k) for k in ('phase','playing','audio_output_state','voice_enabled')}
print(json.dumps(out))
