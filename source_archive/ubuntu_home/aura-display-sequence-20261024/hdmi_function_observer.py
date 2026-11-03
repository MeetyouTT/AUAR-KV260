SNAPSHOT_CODE="import hashlib,json,re,subprocess,time,urllib.request\nfrom pathlib import Path\nv={'scope':'cached-only display snapshot; no AUX/DDC/USB/splitter writes or modeset',\n 'boot':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),'mono_ns':time.monotonic_ns(),\n 'uptime':Path('/proc/uptime').read_text().split()[0]}\ndef read(p):\n try:return Path(p).read_text().strip()\n except OSError:return None\nv['connectors']={}\nfor p in Path('/sys/class/drm').glob('card*-DP-*'):\n raw=(p/'edid').read_bytes();v['connectors'][p.name]={k:read(p/k) for k in ['status','enabled','dpms','modes']}\n v['connectors'][p.name].update(edid_bytes=len(raw),edid_sha256=hashlib.sha256(raw).hexdigest())\nstate=read('/sys/kernel/debug/dri/0/state') or ''\nv['scanout']=[s.strip() for s in state.splitlines() if any(k in s for k in ['format=','size=','pitch=','crtc-pos=','mode:']) or s.strip().startswith(('enable=','active='))]\nv['display_clocks']=[s.strip() for s in (read('/sys/kernel/debug/clk/clk_summary') or '').splitlines() if s.split() and s.split()[0] in ['dp_video_ref','dpdma_ref','dp_aclk']]\nv['hashes']={p:hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in ['/boot/uEnv.txt','/etc/X11/xorg.conf']}\nv['fbdev_emulation']=read('/sys/module/drm_kms_helper/parameters/fbdev_emulation')\nv['fb_nodes']=[p.name for p in Path('/sys/class/graphics').glob('fb*')]\nv['xorg_initial_mode']=[s.strip() for s in (read('/var/log/Xorg.0.log') or '').splitlines() if 'initial mode' in s.lower()]\nv['usb_devices']={p.name:{k:read(p/k) for k in ['idVendor','idProduct','product','busnum','devnum']} for p in Path('/sys/bus/usb/devices').glob('*') if (p/'idVendor').exists()}\nv['units']=subprocess.check_output(['systemctl','show','aura-avatar-ui.service','aura-camera-ui.service','xserver-nodm.service','-p','Id','-p','ActiveState','-p','MainPID','-p','NRestarts'],text=True)\nkernel=subprocess.check_output(['dmesg'],text=True)\nv['kernel_display']=[s for s in kernel.splitlines() if re.search(r'zynqmp-display|dpdma|aux.*(?:fail|error)|training|underflow|drm.*(?:edid|hotplug)',s,re.I)][-50:]\nop=urllib.request.build_opener(urllib.request.ProxyHandler({}))\nfor key,port,path,fields in [('camera',8790,'/health',['pid','detected_frames','capture_hz','detection_hz','camera_error','detector_error']),('gui',8783,'/api/state',['phase','playing','ui_page','backend'])]:\n try:\n  with op.open('http://127.0.0.1:'+str(port)+path,timeout=3) as response:h=json.load(response)\n  v[key]={n:h.get(n) for n in fields}\n except Exception as e:v[key]={'unavailable':type(e).__name__}\nprint(json.dumps(v))\n"
import hashlib,json,os,re,signal,subprocess,sys,time
from pathlib import Path
BOOT='25b3d8ed-84e5-4a81-a2d6-6c8de1733a5f'
SOURCE=Path(sys._getframe().f_code.co_filename).resolve();TOKEN=hashlib.sha256(SOURCE.read_bytes()).hexdigest()[:16]
ROOT=Path('/home/root/aura-display-sequence-20261024')/TOKEN
TRACE=Path('/sys/kernel/tracing/instances')/('aura_hdmi_'+TOKEN)
FUNCTIONS=['zynqmp_dp_hpd_work_func','zynqmp_dp_train_loop','zynqmp_dp_adjust_train','zynqmp_dp_aux_transfer','zynqmp_dp_encoder_enable','zynqmp_dp_encoder_disable','zynqmp_dp_encoder_atomic_mode_set','zynqmp_dp_encoder_mode_set_stream','zynqmp_dp_mode_configure','zynqmp_dp_connector_get_modes']
STOP=False

def write(p,v):Path(p).write_text(v)
def cmd(args,timeout=8):
 p=subprocess.run(args,capture_output=True,text=True,timeout=timeout)
 assert p.returncode==0,p.stderr[-500:]
 return p.stdout
def snapshot():return json.loads(cmd(['/usr/bin/python3','-B','-c',SNAPSHOT_CODE],15))
def cached():
 values={}
 for p in Path('/sys/class/drm').glob('card*-DP-*'):
  raw=(p/'edid').read_bytes();values[p.name]={k:(p/k).read_text().strip() for k in ['status','enabled','dpms']}
  values[p.name].update(edid_bytes=len(raw),edid_sha256=hashlib.sha256(raw).hexdigest())
 return values

def off():
 if TRACE.exists():
  write(TRACE/'tracing_on','0');write(TRACE/'current_tracer','nop');write(TRACE/'set_ftrace_filter','')

def observe():
 global STOP
 assert not TRACE.exists();TRACE.mkdir()
 (ROOT/'before.json').write_text(json.dumps(snapshot(),indent=2)+'\n')
 available={line.split()[0] for line in Path('/sys/kernel/tracing/available_filter_functions').read_text().splitlines()}
 selected=[name for name in FUNCTIONS if name in available];assert 'zynqmp_dp_train_loop' in selected
 report={'boot':BOOT,'scope':'bounded filtered kernel function observations and cached display values',
  'traced_functions':selected,'display_control_commands':0,'aux_requests_initiated_by_observer':0,
  'source_probe_code_sha256':hashlib.sha256(SNAPSHOT_CODE.encode()).hexdigest(),'function_events':[],
  'physical_action_result':'awaiting_user','cleanup_passed':False}
 monitor=None;start=previous=time.monotonic();count=0;last=None;changes=[]
 def stopping(*args):
  global STOP;STOP=True
 signal.signal(signal.SIGTERM,stopping);signal.signal(signal.SIGINT,stopping)
 try:
  write(TRACE/'tracing_on','0');write(TRACE/'buffer_size_kb','64');write(TRACE/'trace_clock','mono')
  write(TRACE/'set_ftrace_filter','\n'.join(selected)+'\n');write(TRACE/'current_tracer','function')
  timer='aura-hdmi-trace-cleanup-'+TOKEN
  cmd(['systemd-run','--quiet','--unit='+timer,'--on-active=200s','/usr/bin/python3','-B',str(SOURCE),'--off'])
  event_file=(ROOT/'drm-events.private.txt').open('w')
  monitor=subprocess.Popen(['udevadm','monitor','--kernel','--property','--subsystem-match=drm'],stdout=event_file,stderr=subprocess.STDOUT)
  write(TRACE/'tracing_on','1')
  (ROOT/'state.json').write_text(json.dumps({'phase':'OBSERVING','boot':BOOT,'started_mono_ns':time.monotonic_ns(),'trace_instance':str(TRACE)})+'\n')
  while not STOP and time.monotonic()-start<180:
   now=time.monotonic();count+=1;state=cached()
   if state!=last:
    changes.append({'mono_ns':time.monotonic_ns(),'elapsed_seconds':now-start,'cached':state});last=state
    (ROOT/'changes.json').write_text(json.dumps(changes,indent=2)+'\n')
   if (ROOT/'finish').exists():
    finish=json.loads((ROOT/'finish').read_text())
    if time.monotonic_ns()-finish['requested_mono_ns']>5_000_000_000:break
   time.sleep(.1)
 finally:
  write(TRACE/'tracing_on','0')
  raw=(TRACE/'trace').read_text();(ROOT/'function-trace.private.txt').write_text(raw)
  report['function_events']=[row for row in raw.splitlines() if row and not row.startswith('#')]
  report['trace_header']=[row for row in raw.splitlines() if row.startswith('#')][:12]
  off()
  if monitor is not None:
   monitor.terminate()
   try:monitor.wait(timeout=3)
   except subprocess.TimeoutExpired:monitor.kill();monitor.wait()
   event_file.close()
  report['cached_changes']=changes;report['samples']=count;report['duration_seconds']=time.monotonic()-start
  report['before']=json.loads((ROOT/'before.json').read_text());report['after']=snapshot()
  if (ROOT/'drm-events.private.txt').exists():
   text=(ROOT/'drm-events.private.txt').read_text();report['drm_events']=[row for row in text.splitlines() if row.startswith(('KERNEL','HOTPLUG=','ACTION=','CONNECTOR='))]
  for p in [ROOT/'action-request.json',ROOT/'finish']:
   if p.exists():report[p.name]=json.loads(p.read_text())
  try:cmd(['systemctl','stop','aura-hdmi-trace-cleanup-'+TOKEN+'.timer'])
  except Exception:pass
  TRACE.rmdir();report['cleanup_passed']=not TRACE.exists()
  (ROOT/'result.json').write_text(json.dumps(report,indent=2)+'\n')
  (ROOT/'state.json').write_text(json.dumps({'phase':'COMPLETE','report':str(ROOT/'result.json')})+'\n')

assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==BOOT
if sys.argv[1:]==['--off']:off()
elif sys.argv[1:]==['--observe']:observe()
else:
 assert not sys.argv[1:];ROOT.mkdir(parents=True,exist_ok=False,mode=0o700)
 cmd(['systemd-run','--no-block','--quiet','--unit=aura-hdmi-observer-'+TOKEN,
  '--property=Type=oneshot','--property=RuntimeMaxSec=190','/usr/bin/python3','-B',str(SOURCE),'--observe'])
 until=time.monotonic()+5
 while time.monotonic()<until and not (ROOT/'state.json').exists():time.sleep(.1)
 assert (ROOT/'state.json').exists(),'Observer did not enter ready state'
 print(json.dumps({'ready':True,'root':str(ROOT),'boot':BOOT,'functions':FUNCTIONS,'display_control_commands':0}))
