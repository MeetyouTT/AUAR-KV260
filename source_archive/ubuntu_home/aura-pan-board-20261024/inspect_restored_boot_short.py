import hashlib,json,subprocess,urllib.request
from pathlib import Path
def read(p):
 try:return Path(p).read_bytes()
 except OSError:return None
def get(port,path):
 o=urllib.request.build_opener(urllib.request.ProxyHandler({}))
 with o.open('http://127.0.0.1:%d%s'%(port,path),timeout=2) as r:return json.load(r)
boot=read('/proc/sys/kernel/random/boot_id');fdt=read('/sys/firmware/fdt');fw=read('/proc/device-tree/fpga-full/firmware-name')
d=dict(boot_id=boot.decode().strip() if boot else None,fdt_sha256=hashlib.sha256(fdt).hexdigest() if fdt else None,
 firmware=fw.rstrip(b'\0').decode() if fw else None,fpga_state=read('/sys/class/fpga_manager/fpga0/state').decode().strip(),
 vart=read('/etc/vart.conf').decode().strip(),units={},MMIO_opened=False,ARM=0,COMMIT=0,services_modified=False)
for unit in ['aura-camera-ui.service','aura-avatar-ui.service','aura-face-zone-editor.service']:
 p=subprocess.run(['systemctl','show',unit,'-p','MainPID','-p','ActiveState','-p','SubState','-p','Result','-p','ExecMainStatus','-p','NRestarts'],capture_output=True,text=True,timeout=4)
 d['units'][unit]=dict(s.split('=',1) for s in p.stdout.splitlines() if '=' in s)
for name,port,path in [('camera',8790,'/health'),('ui',8783,'/api/state')]:
 try:
  v=get(port,path)
  if name=='camera':
   s=v.get('dpu_schedule') or {};i=v.get('identity') or {}
   d[name]=dict(pid=v.get('pid'),identity_ready=i.get('ready'),identity_error=i.get('error'),owner_fenced=s.get('owner_fenced'),
    primary_overruns=s.get('primary_period_overruns'),optional={k:{'overruns':x.get('overruns'),'state':x.get('state')} for k,x in s.get('optional',{}).items()})
  else:d[name]=dict(manual=v.get('manual_pan'),page=v.get('ui_page'),preview=(v.get('ui_runtime') or {}).get('preview_metrics'))
 except Exception as e:d[name]=dict(error_type=type(e).__name__)
print(json.dumps(d))
