"""Inspect scanout and window bounds after reported black screen corners."""
import hashlib,json,os,re,subprocess,urllib.request
from pathlib import Path
env=dict(os.environ,DISPLAY=':0')
def cmd(args):
 try:
  p=subprocess.run(args,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=5)
  return {'rc':p.returncode,'text':p.stdout[-14000:]}
 except Exception as e:return {'unavailable':str(e)}
v={'boot_id':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
 'xrandr':cmd(['xrandr','--verbose']), 'dpms':cmd(['xset','q']),
 'drm_state':cmd(['cat','/sys/kernel/debug/dri/0/state']),
 'root':cmd(['xprop','-root','_NET_ACTIVE_WINDOW','_NET_WORKAREA','_NET_DESKTOP_GEOMETRY']),
 'files_modified':0,'display_commands_sent':0,'movement_commands_sent':0}
ids=re.findall(r'0x[0-9a-fA-F]+',v['root'].get('text',''))
if ids:v['window']=cmd(['xprop','-id',ids[0],'_NET_WM_NAME','_NET_WM_PID','_NET_WM_STATE','_NET_FRAME_EXTENTS'])
depth=cmd(['xdpyinfo'])
v['geometry']=[s for s in depth.get('text','').splitlines() if any(k in s for k in ['dimensions:','resolution:','depth of root window:'])]
v['connectors']=[]
for p in Path('/sys/class/drm').glob('card*-*/edid'):
 raw=p.read_bytes();row={'path':str(p.parent),'edid_bytes':len(raw),'edid_sha256':hashlib.sha256(raw).hexdigest() if raw else None}
 for k in ['status','enabled','dpms']:
  q=p.with_name(k)
  if q.exists():row[k]=q.read_text().strip()
 v['connectors'].append(row)
opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
with opener.open('http://127.0.0.1:8783/api/state',timeout=2) as response:state=json.load(response)
v['ui']={k:state.get(k) for k in ['phase','ui_page','ui_layer','error']}
v['settings']={k:state.get('ui_settings',{}).get(k) for k in ['fullscreen','economy']}
print(json.dumps(v),flush=True)
