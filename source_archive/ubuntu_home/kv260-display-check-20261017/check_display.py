"""Read the board display state; optionally wake it without changing timeouts."""
import argparse
import base64
import datetime
import hashlib
import importlib.util
import json
from pathlib import Path


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--wake', action='store_true', help='Wake the existing X11 display')
parser.add_argument('--deep', action='store_true', help='Inspect scanout, EDID, logs and attached peripherals')
parser.add_argument('--retrain', action='store_true', help='Re-enable the current 1024x600 DP output to retrain its link')
parser.add_argument('--hdmi', action='store_true', help='Inspect the HDMI path through DP AUX, live EDID and display clocks')
parser.add_argument('--usb', action='store_true', help='Inspect USB topology, the onboard hub and camera enumeration only')
parser.add_argument('--avatar', action='store_true', help='Show the existing avatar interaction page')
parser.add_argument('--source', help='Run a reviewed Python probe from this work directory')
args = parser.parse_args()
wire = module('display_wire', '/home/ghmd/aura-board-ui-autostart-20261009/manage_startup.py')
baseline = module('display_baseline', '/home/ghmd/aura-board-avatar-baseline-20261009/read_board_environment.py')
probes = {
    'display': baseline.PROBES['display'],
    'ui_power': '''
import json,os,subprocess,urllib.request
from pathlib import Path
def run(args):
 try:
  p=subprocess.run(args,env=dict(os.environ,DISPLAY=':0'),stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=5)
  return {'exit_code':p.returncode,'output':p.stdout}
 except Exception as e:return {'error':str(e)}
r={'boot_id':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
 'xset':run(['xset','q']),
 'service':run(['systemctl','show','aura-avatar-ui.service','xserver-nodm.service','-p','Id','-p','ActiveState','-p','SubState','-p','MainPID'])}
try:
 with urllib.request.urlopen('http://127.0.0.1:8783/api/state',timeout=4) as f:v=json.load(f)
 r['ui']={k:v.get(k) for k in ['ui_page','ui_layer','phase','error','ui_settings']}
except Exception as e:r['ui']={'error':str(e)}
print(json.dumps(r,ensure_ascii=False))
''',
    'screen': '''
import base64,hashlib,io,json,os
from pathlib import Path
os.environ['DISPLAY']=':0'
p=Path('/home/root/aura-avatar-gtk-stage/runtime-1a8677ce-20261009/aura/tools/board_screen_capture.py')
scope={'__name__':'display_readonly_capture'}
exec(compile(p.read_text().replace('image.save(str(path),','image.save(path,'),str(p),'exec'),scope)
buf=io.BytesIO();size=scope['capture'](buf)
from PIL import Image
out=io.BytesIO();Image.open(io.BytesIO(buf.getvalue())).save(out,format='JPEG',quality=72)
d=out.getvalue()
print(json.dumps({'size':size,'bytes':len(d),'sha256':hashlib.sha256(d).hexdigest(),'base64':base64.b64encode(d).decode()}))
''',
}
if args.hdmi:
    hdmi = '''
import hashlib,json,os,subprocess,time
from pathlib import Path
def read(p):
 try:return Path(p).read_text().strip()
 except OSError as e:return {'error':str(e)}
p=Path('/sys/class/drm/card0-DP-1')
samples=[]
for i in range(3):
 q=subprocess.run(['xrandr','--display',':0','--props'],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=8)
 d=(p/'edid').read_bytes()
 samples.append({'index':i,'status':read(p/'status'),'enabled':read(p/'enabled'),'dpms':read(p/'dpms'),
 'edid_bytes':len(d),'edid_sha256':hashlib.sha256(d).hexdigest(),'edid_hex':d.hex(),'query_code':q.returncode})
 time.sleep(.4)
aux=[]
for dev in Path('/dev').glob('drm_dp_aux*'):
 r={'device':str(dev),'name':read(Path('/sys/class/drm_dp_aux_dev')/dev.name/'name'),'registers':{}}
 try:
  fd=os.open(str(dev),os.O_RDONLY)
  try:
   for name,offset,count in [('capabilities',0,16),('link_config',0x100,2),('link_status',0x200,8),('power',0x600,1)]:
    try:r['registers'][name]=os.pread(fd,count,offset).hex()
    except OSError as e:r['registers'][name]={'error':str(e)}
  finally:os.close(fd)
 except OSError as e:r['error']=str(e)
 aux.append(r)
c=Path('/sys/kernel/debug/clk/clk_summary')
clocks=[l for l in c.read_text().splitlines() if any(k in l.lower() for k in ['dpll','dpdma','dp_video','dp_audio','dp_ref'])] if c.exists() else []
q=subprocess.run(['dmesg'],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=5)
lines=[l for l in q.stdout.splitlines() if any(k in l.lower() for k in ['fd4a0000','hdmi','edid','aux','training','underflow','dpdma','dpll'])]
print(json.dumps({'samples':samples,'aux':aux,'clock_lines':clocks,'display_log':lines[-70:],
 'debug_files':[x.name for x in Path('/sys/kernel/debug/dri/0').iterdir()]}))
'''
    probes = {'hdmi_link': hdmi, **probes}
if args.deep:
    common = '''
import hashlib,json,os,subprocess
from pathlib import Path
def run(args):
 try:
  p=subprocess.run(args,env=dict(os.environ,DISPLAY=':0'),stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=10)
  return {'exit_code':p.returncode,'output':p.stdout[-18000:]}
 except Exception as e:return {'error':str(e)}
def read(path):
 try:return Path(path).read_text()[-20000:]
 except OSError as e:return {'error':str(e)}
'''
    diagnostics = {
        'xorg_details': common + '''
logs={}
for p in ['/var/log/Xorg.0.log','/home/root/.local/share/xorg/Xorg.0.log']:
 if Path(p).is_file():logs[p]=read(p)
r={'xrandr_verbose':run(['xrandr','--verbose']),'xset':run(['xset','q']),'logs':logs}
print(json.dumps(r))
''',
        'scanout': common + '''
p=Path('/sys/class/drm/card0-DP-1/edid')
edid=p.read_bytes()
r={'modetest':run(['modetest','-D','fd4a0000.display','-c','-p']),
 'drm_state':read('/sys/kernel/debug/dri/0/state'),
 'edid':{'bytes':len(edid),'hex':edid.hex(),'sha256':hashlib.sha256(edid).hexdigest()},
 'framebuffers':{str(p):read(p) for p in Path('/sys/class/graphics').glob('fb*/blank')}}
print(json.dumps(r))
''',
        'peripherals_logs': common + '''
usb=[]
for p in Path('/sys/bus/usb/devices').iterdir():
 if (p/'idVendor').exists():usb.append({n:read(p/n).strip() if isinstance(read(p/n),str) else read(p/n) for n in ['idVendor','idProduct','product']})
backlights={str(p):{n:read(p/n) for n in ['brightness','actual_brightness','bl_power','max_brightness']} for p in Path('/sys/class/backlight').iterdir()}
keys=['fd4a0000','display','xlnx-dp','dpdma','aux','hdmi','edid','usb','underflow','clock']
full=subprocess.run(['dmesg'],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=5)
d={'exit_code':full.returncode,'output':'\\n'.join(l for l in full.stdout.splitlines() if any(k in l.lower() for k in keys))[-18000:]}
print(json.dumps({'usb':usb,'backlights':backlights,'dmesg':d}))
''',
    }
    probes = {**diagnostics, **probes}
if args.retrain:
    retrain = '''
import json,os,subprocess,time
from pathlib import Path
env=dict(os.environ,DISPLAY=':0')
def run(args):
 p=subprocess.run(args,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=10)
 return {'args':args,'exit_code':p.returncode,'output':p.stdout}
before=run(['xrandr','--current'])
assert before['exit_code']==0 and 'DP-1 connected primary 1024x600' in before['output'],before
actions=[]
try:
 actions.append(run(['xrandr','--output','DP-1','--off']))
 time.sleep(1)
finally:
 actions.append(run(['xrandr','--output','DP-1','--mode','1024x600','--rate','59.85']))
actions.append(run(['xset','s','reset']))
actions.append(run(['xset','dpms','force','on']))
time.sleep(2)
after=run(['xrandr','--verbose'])
edid=Path('/sys/class/drm/card0-DP-1/edid').read_bytes()
print(json.dumps({'before':before,'actions':actions,'after':after,'edid_bytes':len(edid)}))
raise SystemExit(0 if all(a['exit_code']==0 for a in actions) else 1)
'''
    probes = {'retrain': retrain, **probes}
if args.wake:
    wake = '''
import json,os,subprocess,time
from pathlib import Path
env=dict(os.environ,DISPLAY=':0')
def run(args):
 p=subprocess.run(args,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=5)
 return {'args':args,'exit_code':p.returncode,'output':p.stdout}
before=run(['xset','q'])
actions=[run(['xset','s','reset']),run(['xset','dpms','force','on'])]
time.sleep(2)
after=run(['xset','q'])
p=Path('/sys/class/drm/card0-DP-1')
drm={n:(p/n).read_text().strip() for n in ['status','enabled','dpms']}
ok=all(a['exit_code']==0 for a in actions) and after['exit_code']==0 and 'Monitor is On' in after['output'] and drm=={'status':'connected','enabled':'enabled','dpms':'On'}
print(json.dumps({'before':before,'actions':actions,'after':after,'drm':drm,'wake_verified':ok}))
raise SystemExit(0 if ok else 1)
'''
    probes = {'wake': wake, **probes}
if args.usb:
    common_usb = '''
import json,subprocess,urllib.request
from pathlib import Path
def read(p):
 try:return Path(p).read_text().strip()
 except OSError as e:return {'error':str(e)}
def run(args):
 try:
  p=subprocess.run(args,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=8)
  return {'exit_code':p.returncode,'output':p.stdout[-14000:]}
 except Exception as e:return {'error':str(e)}
'''
    probes = {
        'usb_topology': common_usb + '''
devices=[]
for p in sorted(Path('/sys/bus/usb/devices').iterdir()):
 if not (p/'idVendor').exists():continue
 fields=['idVendor','idProduct','manufacturer','product','speed','busnum','devnum','maxchild','authorized','power/control','power/runtime_status']
 devices.append({'path':p.name,'values':{n:read(p/n) for n in fields}})
ports={str(p):{n:read(p/n) for n in ['connect_type','state','disable','power/control','power/runtime_status']} for p in Path('/sys/bus/usb/devices').glob('*/usb*-port*')}
print(json.dumps({'boot_id':read('/proc/sys/kernel/random/boot_id'),'devices':devices,'ports':ports,'lsusb':run(['lsusb']),'tree':run(['lsusb','-t'])}))
''',
        'usb_hub_control': common_usb + '''
p=Path('/sys/bus/i2c/devices/1-002d')
hub={'exists':p.exists(),'name':read(p/'name'),'driver':str((p/'driver').resolve()) if (p/'driver').exists() else None,
 'power':{n:read(p/n) for n in ['power/control','power/runtime_status']}}
drivers={str(p):[x.name for x in p.iterdir()] for p in [Path('/sys/bus/i2c/drivers/usb5744'),Path('/sys/bus/platform/drivers/xhci-hcd')] if p.exists()}
print(json.dumps({'hub_control':hub,'drivers':drivers,'uvc_registered':Path('/sys/bus/usb/drivers/uvcvideo').is_dir(),'uvc_module':run(['modinfo','uvcvideo']),'gpio':read('/sys/kernel/debug/gpio')}))
''',
        'camera_enumeration': common_usb + '''
videos={}
for p in Path('/sys/class/video4linux').glob('video*'):
 videos[p.name]={'name':read(p/'name'),'device':str((p/'device').resolve()),'capabilities':run(['v4l2-ctl','-d','/dev/'+p.name,'--all'])}
service=run(['systemctl','show','aura-camera-ui.service','-p','ActiveState','-p','SubState','-p','MainPID','-p','NRestarts'])
try:
 with urllib.request.urlopen('http://127.0.0.1:8790/health',timeout=3) as f:health=json.load(f)
except Exception as e:health={'error':str(e)}
q=subprocess.run(['dmesg'],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=5)
lines=[l for l in q.stdout.splitlines() if any(k in l.lower() for k in ['usb ','usb5744','usb2734','usb5734','uvc','over-current'])]
print(json.dumps({'video_nodes':[str(p) for p in Path('/dev').glob('video*')],'video_devices':videos,
 'list_devices':run(['v4l2-ctl','--list-devices']),'service':service,'health':health,'usb_log_tail':lines[-65:]},ensure_ascii=False))
''',
    }
if args.avatar:
    avatar = '''
import json,time,urllib.request
def api(data=None):
 base='http://127.0.0.1:8783'
 req=base+'/api/state' if data is None else urllib.request.Request(base+'/api/command',data=json.dumps(data).encode(),headers={'Content-Type':'application/json','Origin':base})
 with urllib.request.urlopen(req,timeout=4) as f:return json.load(f)
def view(s):
 return {k:s.get(k) for k in ['ui_page','ui_layer','phase','error','avatar_renderer']}
before=view(api())
response=api({'type':'ui_page','page':'main'})
assert response.get('ok'),response
deadline=time.monotonic()+6
while True:
 after=api()
 if after.get('ui_page')=='main' and after.get('ui_layer')=='presentation':break
 assert time.monotonic()<deadline,'Avatar page did not become active'
 time.sleep(.1)
first=view(after);time.sleep(1);second=view(api())
print(json.dumps({'before':before,'command':response,'after':first,'later':second},ensure_ascii=False))
'''
    probes = {'avatar_page': avatar, **probes}
if args.source:
    source = Path(args.source).resolve(strict=True)
    if source.parent != Path(__file__).resolve().parent:
        raise ValueError('Probe must belong to this work directory')
    probes = {source.stem: source.read_text()}
commands = [(name, wire.wire(code)) for name, code in probes.items()]
stamp = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')
folder = Path(__file__).resolve().parent / 'evidence' / stamp
folder.mkdir(parents=True, exist_ok=False)
status = {'complete': False, 'responses': []}
uart = None
try:
    with (folder / 'serial.raw').open('xb') as raw:
        try:
            uart = wire.transport_module().UART(raw)
            uart.connect()
            for index, (name, command) in enumerate(commands):
                (folder / (name + '.command')).write_text(command)
                rc, data, digest = uart.command(command, 'DISPLAY%03d' % index, 45)
                (folder / (name + '.output')).write_bytes(data)
                status['responses'].append({'name': name, 'exit_code': rc, 'sha256': digest})
                if rc:
                    raise RuntimeError(data.decode(errors='replace')[-1500:])
                value = json.loads(data)
                if name == 'screen':
                    image = base64.b64decode(value.pop('base64'), validate=True)
                    assert len(image) == value['bytes']
                    assert hashlib.sha256(image).hexdigest() == value['sha256']
                    (folder / 'screen.jpg').write_bytes(image)
                (folder / (name + '.json')).write_text(json.dumps(value, ensure_ascii=False, indent=2))
                visible = value if name in ('display', 'ui_power', 'screen', 'wake') else {'saved': str(folder / (name + '.json'))}
                print(json.dumps({'probe': name, 'result': visible}, ensure_ascii=False), flush=True)
            status['complete'] = True
        finally:
            if uart:
                status['console_echo_restored'] = uart.close()
except Exception as exc:
    status['error'] = type(exc).__name__ + ': ' + str(exc)
(folder / 'result.json').write_text(json.dumps(status, indent=2))
print(json.dumps({'evidence': str(folder), **status}), flush=True)
raise SystemExit(0 if status['complete'] else 1)
