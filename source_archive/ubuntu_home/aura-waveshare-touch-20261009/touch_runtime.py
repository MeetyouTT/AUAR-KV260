#!/usr/bin/env python3
"""Recover the owned UI session and verify the real Waveshare input device."""
import argparse
import base64
import datetime
import gzip
import hashlib
import importlib.util
import json
from pathlib import Path
import shlex

ROOT = Path(__file__).resolve().parent
TRANSPORT = Path('/home/ghmd/kv260-dfx-state-boardtest-20261004/scripts/uart_phase.py')
PRELUDE = r'''
import hashlib,json,os,subprocess,time,urllib.request
from pathlib import Path
root=Path('/home/root/aura-avatar-gtk-stage/runtime-1a8677ce-20261009')
env=dict(os.environ,DISPLAY=':0',PYTHONUNBUFFERED='1')
def state():
 with urllib.request.urlopen('http://127.0.0.1:8783/api/state',timeout=5) as r:return json.load(r)
def command(data):
 q=urllib.request.Request('http://127.0.0.1:8783/api/command',data=json.dumps(data).encode(),headers={'Content-Type':'application/json','Origin':'http://127.0.0.1:8783'})
 with urllib.request.urlopen(q,timeout=12) as r:return json.load(r)
def run(args):
 p=subprocess.run(args,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=12)
 assert p.returncode==0,(args,p.stdout)
 return p.stdout
'''
PHASES = {
    'autostart-inspect': r'''
files={}
for name in ['/etc/init.d/xserver-nodm','/etc/default/xserver-nodm','/etc/X11/Xserver','/etc/X11/Xsession']:
 p=Path(name)
 if p.is_file():files[name]=p.read_text(errors='replace')[:12000]
checks={}
for name,args in [('version',['systemctl','--version']),('units',['systemctl','list-unit-files','xserver*','display-manager*','graphical.target','multi-user.target']),('xserver',['systemctl','cat','xserver-nodm.service']),('default',['systemctl','get-default']),('failed',['systemctl','--failed','--no-pager'])]:
 p=subprocess.run(args,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=12)
 checks[name]={'returncode':p.returncode,'output':p.stdout}
processes=[]
for p in Path('/proc').iterdir():
 if not p.name.isdigit():continue
 try:
  args=(p/'cmdline').read_bytes().decode(errors='replace').strip(chr(0)).split(chr(0))
  if not any(Path(a).name in ['Xorg','X','board_avatar_gtk.py','xinit','xserver-nodm'] for a in args if a):continue
  selected={}
  for item in (p/'environ').read_bytes().decode(errors='replace').split(chr(0)):
   k,sep,v=item.partition('=')
   if sep and k in ['DISPLAY','XAUTHORITY','USER','DBUS_SESSION_BUS_ADDRESS']:selected[k]=v
  processes.append({'pid':int(p.name),'args':args,'environment':selected})
 except OSError:continue
autostart={}
for name in ['/etc/xdg/autostart','/home/root/.config/autostart','/etc/systemd/system']:
 p=Path(name)
 if p.is_dir():autostart[name]=sorted(x.name for x in p.iterdir())
try:ui=state()
except Exception as e:ui={'api_error':str(e)}
print(json.dumps({'checks':checks,'files':files,'processes':processes,'autostart':autostart,'state':ui,'boot_id':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),'disk_free':__import__('shutil').disk_usage(str(root)).free},ensure_ascii=False))
''',
    'display': r'''
before=run(['xrandr','--verbose'])
edid=Path('/sys/class/drm/card0-DP-1/edid').read_bytes()
assert hashlib.sha256(edid).hexdigest()=='727d3e1893df759c757c35232f9465b670a64d6de2011b586de48c6446e17c35'
assert '1024x600' in before and '+preferred' in before
run(['xset','dpms','force','on'])
run(['xrandr','--output','DP-1','--mode','1024x600','--rate','59.85'])
after=run(['xrandr','--current'])
assert 'DP-1 connected primary 1024x600+0+0' in after,after
names=run(['xinput','list','--name-only']).splitlines()
touch=[s for s in names if s.strip()=='WaveShare WS170120']
assert len(touch)==1,names
run(['xinput','map-to-output','WaveShare WS170120','DP-1'])
print(json.dumps({'complete':True,'display_before':before,'display_after':after,'touch_properties':run(['xinput','list-props','WaveShare WS170120']),'touch_classes':run(['xinput','list','--long','WaveShare WS170120']),'edid_sha256':hashlib.sha256(edid).hexdigest()}))
''',
    'start': r'''
import socket
source=root/'aura/tools/board_avatar_gtk.py'
assert hashlib.sha256(source.read_bytes()).hexdigest()=='dbf55275035374221db1303bcf7549b54a6e0821dfa352fda41bb63df7cd7e7e'
boot=Path('/proc/sys/kernel/random/boot_id').read_text().strip()
old=json.loads((root/'launch.json').read_text())
assert old['boot_id']!=boot
for p in Path('/proc').iterdir():
 if not p.name.isdigit():continue
 try:assert str(source) not in (p/'cmdline').read_bytes().decode(errors='replace').split(chr(0))
 except OSError:pass
with socket.socket() as s:s.bind(('127.0.0.1',8783))
backup=root/('recovery-backup-'+boot);backup.mkdir(exist_ok=False)
for name in ['launch.json','stage.log']:
 p=root/name
 if p.exists():p.rename(backup/name)
evidence=root/('run-evidence-'+boot)
assert not evidence.exists()
args=['python3','-B',str(source),'--evidence-root',str(evidence)]
with (root/'stage.log').open('xb') as log:
 p=subprocess.Popen(args,cwd=str(root/'aura'),env=env,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
info={'pid':p.pid,'args':args,'evidence':str(evidence),'boot_id':boot,'recovered_previous':str(backup)}
with (root/'launch.json').open('x') as f:json.dump(info,f,indent=2);f.flush();os.fsync(f.fileno())
print(json.dumps(info))
''',
    'status': r'''
info=json.loads((root/'launch.json').read_text())
try:ui=state()
except Exception as e:ui={'api_error':str(e)}
print(json.dumps({'launch':info,'state':ui,'log':(root/'stage.log').read_text()[-3000:],'display':run(['xrandr','--current']),'touch_properties':run(['xinput','list-props','WaveShare WS170120']),'touch_classes':run(['xinput','list','--long','WaveShare WS170120'])},ensure_ascii=False))
''',
    'settings-page': r'''
result=command({'type':'ui_page','page':'settings'})
assert result['ok'],result
time.sleep(.5)
print(json.dumps({'command':result,'state':state()},ensure_ascii=False))
''',
    'report': r'''
record=command({'type':'save_evidence'})
assert record['ok'],record
report=json.loads(Path(record['report']).read_text())
keys=['ui_page','ui_settings','preferences','touch_devices','input_events','errors','stats','source_hashes_at_launch']
print(json.dumps({'record':record,**{k:report.get(k) for k in keys}},ensure_ascii=False))
''',
    'window': r'''
import base64,io
from PIL import Image
info=json.loads((root/'launch.json').read_text());folder=Path(info['evidence'])
p=max(folder.glob('window_*.png'),key=lambda x:x.stat().st_mtime_ns)
image=Image.open(p).convert('RGB');out=io.BytesIO();image.save(out,format='JPEG',quality=72)
data=out.getvalue()
print(json.dumps({'source':str(p),'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest(),'jpeg_base64':base64.b64encode(data).decode()}))
''',
    'observe': r'''
import fcntl,select,struct
from collections import deque
devices=[]
for e in Path('/sys/class/input').glob('event*'):
 d=e/'device'
 if (d/'id/vendor').read_text().strip()=='0eef' and (d/'id/product').read_text().strip()=='0005' and int((d/'properties').read_text().strip().split()[-1],16)&2:devices.append(e)
assert len(devices)==1,devices
device=devices[0];fd=os.open('/dev/input/'+device.name,os.O_RDONLY|os.O_NONBLOCK)
event=struct.Struct('llHHi');events=deque(maxlen=600);counts={};axes={}
for code in [0,1,53,54]:
 data=bytearray(24);fcntl.ioctl(fd,0x80184540+code,data,True);axes[code]=struct.unpack('6i',data)
before=state();end=time.monotonic()+25;total=0;buffer=b''
try:
 while time.monotonic()<end:
  if not select.select([fd],[],[],.2)[0]:continue
  buffer+=os.read(fd,4096)
  while len(buffer)>=event.size:
   sec,usec,kind,code,value=event.unpack(buffer[:event.size]);buffer=buffer[event.size:]
   total+=1;key=str(kind)+':'+str(code);counts[key]=counts.get(key,0)+1
   if kind in [1,3]:events.append({'t':sec+usec/1000000,'type':kind,'code':code,'value':value})
finally:os.close(fd)
print(json.dumps({'physical_device':str(device),'event_bytes':event.size,'seconds':25,'axes':axes,'events_total':total,'event_counts':counts,'events':list(events),'before':before,'after':state(),'method':'READ_ONLY_REAL_EVDEV_NO_GRAB_NO_SYNTHETIC_EVENTS'},ensure_ascii=False))
''',
    'persist-driver': r'''
import shutil
release=os.uname().release;assert release=='5.15.36-xilinx-v2022.2'
source=Path('/home/root/aura-waveshare-touch-20261009/module-fce568b070bbc0e9/hid-multitouch.ko')
sha='fce568b070bbc0e9210bc6417b39e1c57637d9d24d9fdebc4cb913603505417b'
assert hashlib.sha256(source.read_bytes()).hexdigest()==sha
assert Path('/sys/module/hid_multitouch').exists()
assert any((p/'driver').exists() and (p/'driver').resolve().name=='hid-multitouch' for p in Path('/sys/bus/hid/devices').glob('0003:0EEF:0005.*'))
modules=Path('/lib/modules')/release
backup=Path('/home/root/aura-waveshare-touch-20261009')/('module-index-backup-'+str(time.time_ns()))
backup.mkdir()
for p in modules.glob('modules.*'):
 if p.is_file():shutil.copy2(str(p),str(backup/p.name))
target=modules/'extra/aura/hid-multitouch.ko';target.parent.mkdir(parents=True,exist_ok=True)
if not target.exists():
 with source.open('rb') as r,target.open('xb') as w:shutil.copyfileobj(r,w);w.flush();os.fsync(w.fileno())
assert not target.is_symlink() and hashlib.sha256(target.read_bytes()).hexdigest()==sha
run(['depmod','-a',release])
found=run(['modinfo','-F','filename','hid-multitouch']).strip();assert found==str(target),found
conf=Path('/etc/modules-load.d/aura-touch.conf');conf.parent.mkdir(parents=True,exist_ok=True)
if not conf.exists():
 with conf.open('x') as f:f.write('hid-multitouch\n');f.flush();os.fsync(f.fileno())
assert conf.read_text()=='hid-multitouch\n'
print(json.dumps({'complete':True,'module':str(target),'sha256':sha,'autoload':str(conf),'backup':str(backup),'vermagic':run(['modinfo','-F','vermagic','hid-multitouch']).strip(),'boot_tested':False}))
''',
    'verify-final': r'''
info=json.loads((root/'launch.json').read_text());ui=state()
saved=json.loads((root/'avatar_user_settings.json').read_text())
processes={'gui':[],'vision':[],'dfx_manager':[]}
for p in Path('/proc').iterdir():
 if not p.name.isdigit():continue
 try:args=(p/'cmdline').read_bytes().decode(errors='replace').split(chr(0))
 except OSError:continue
 for label,needle in [('gui','board_avatar_gtk.py'),('vision','realtime_vision.py'),('dfx_manager','dfx-mgrd')]:
  if any(Path(a).name==needle for a in args if a):processes[label].append(int(p.name))
hid=[]
for p in Path('/sys/bus/hid/devices').glob('0003:0EEF:0005.*'):
 hid.append({'id':p.name,'driver':(p/'driver').resolve().name})
checks={}
for name,args in [('autoload_service',['systemctl','show','systemd-modules-load.service','-p','LoadState','-p','ActiveState','-p','SubState','-p','Result']),('module_resolution',['modprobe','--show-depends','hid-multitouch'])]:
 p=subprocess.run(args,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=12)
 checks[name]={'returncode':p.returncode,'output':p.stdout}
print(json.dumps({'launch':info,'state':ui,'saved_settings':saved,'alsa':run(['amixer','-c','MCP01','get','PCM']),'processes':processes,'hid':hid,'touch_properties':run(['xinput','list-props','WaveShare WS170120']),'touch_classes':run(['xinput','list','--long','WaveShare WS170120']),'display':run(['xrandr','--current']),'checks':checks,'autoload_config':Path('/etc/modules-load.d/aura-touch.conf').read_text(),'module_sha256':hashlib.sha256(Path('/lib/modules/5.15.36-xilinx-v2022.2/extra/aura/hid-multitouch.ko').read_bytes()).hexdigest()},ensure_ascii=False))
''',
}


def wire(source):
    compile(source,'<touch runtime>','exec')
    data=base64.b64encode(gzip.compress(source.encode(),mtime=0)).decode()
    result='python3 -B -c '+shlex.quote('import base64,gzip;exec(gzip.decompress(base64.b64decode('+repr(data)+')))')
    assert 4*((len(result.encode())+2)//3)+700<=3800, len(result.encode())
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--phase',choices=tuple(PHASES),required=True)
    parser.add_argument('--validate',action='store_true')
    args=parser.parse_args()
    commands={name:wire(PRELUDE+source) for name,source in PHASES.items()}
    if args.validate:
        print(json.dumps({'inner_wire_bytes':{k:len(v.encode()) for k,v in commands.items()},'board_accessed':False}));return 0
    spec=importlib.util.spec_from_file_location('reviewed_uart',str(TRANSPORT))
    transport=importlib.util.module_from_spec(spec);spec.loader.exec_module(transport)
    out=ROOT/'evidence'/datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ-'+args.phase)
    out.mkdir(parents=True);uart=None;status={'phase':args.phase,'complete':False,'command':commands[args.phase]}
    with (out/'serial.raw').open('xb') as raw:
        try:
            uart=transport.UART(raw);uart.connect()
            print(json.dumps({'evidence':str(out),'root_shell_confirmed':True}),flush=True)
            rc,data,digest=uart.command(commands[args.phase],'TR001',55)
            (out/'response.output').write_bytes(data)
            status.update(exit_code=rc,bytes=len(data),sha256=digest,complete=rc==0)
            if rc==0:
                result=json.loads(data)
                if args.phase=='window':
                    image=base64.b64decode(result.pop('jpeg_base64'));assert len(image)==result['bytes'] and hashlib.sha256(image).hexdigest()==result['sha256']
                    (out/'board-window.jpg').write_bytes(image)
                (out/'result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
                print(json.dumps({'result':{k:v for k,v in result.items() if k not in ['events','before','after','input_events','display_before','touch_classes','touch_properties','log']}} ,ensure_ascii=False)[:2400],flush=True)
            else:print(data.decode(errors='replace')[-1800:],flush=True)
        except Exception as exc:status['error']=str(exc)
        finally:
            if uart is not None:status['console_echo_restored']=uart.close()
    (out/'status.json').write_text(json.dumps(status,indent=2)+'\n')
    print(json.dumps({k:v for k,v in status.items() if k!='command'}),flush=True)
    return 0 if status['complete'] and status.get('console_echo_restored') else 1


if __name__=='__main__':raise SystemExit(main())
