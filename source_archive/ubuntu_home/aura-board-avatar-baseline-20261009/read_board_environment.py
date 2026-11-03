#!/usr/bin/env python3
"""Read KV260 prerequisites over its existing, unoccupied root UART console.

No login attempts, firmware loading, process interruption, playback, package
installation, or board file writes. Evidence is saved only on the Ubuntu host.
The existing transport temporarily disables console echo and restores it.
"""
import argparse
import ast
import base64
import datetime
import gzip
import hashlib
import importlib.util
import json
from pathlib import Path
import shlex
import sys
import textwrap


ROOT = Path(__file__).resolve().parent
TRANSPORT = Path('/home/ghmd/kv260-dfx-state-boardtest-20261004/scripts/uart_phase.py')

PROBES = {
    'network_link_and_media': '''
import json,shutil,subprocess
from pathlib import Path
def command(args):
 if not shutil.which(args[0]):return {'available':False}
 try:
  p=subprocess.run(args,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=6,text=True)
  return {'available':True,'exit_code':p.returncode,'output':p.stdout[:6000]}
 except Exception as e:return {'available':True,'error':type(e).__name__+': '+str(e)}
def read(path):
 try:return Path(path).read_text().strip()
 except OSError as e:return {'error':str(e)}
link={key:read('/sys/class/net/eth0/'+key) for key in ['operstate','carrier','flags','speed','duplex']}
roots={}
for base in ['/media','/mnt','/run/media']:
 path=Path(base)
 try:roots[base]=sorted(p.name for p in path.iterdir())[:30] if path.is_dir() else []
 except OSError as e:roots[base]={'error':str(e)}
result={'eth0_sysfs':link,'ethtool':command(['ethtool','eth0']),
 'ip_link':command(['ip','-details','link','show','dev','eth0']),
 'removable_roots':roots,'block_devices':command(['lsblk','-J','-o','NAME,TYPE,RM,SIZE,MOUNTPOINT']),
 'network_manager':command(['nmcli','-t','-f','DEVICE,TYPE,STATE','device','status'])}
print(json.dumps(result,sort_keys=True))
''',
    'identity': '''
import json,os,platform,sys
from pathlib import Path
def read(path):
 try:return Path(path).read_text().strip().replace('\\x00','')
 except OSError:return None
v=os.statvfs('/')
print(json.dumps({'machine':platform.machine(),'kernel':platform.release(),
 'python':sys.version,'model':read('/proc/device-tree/model'),
 'os_release':read('/etc/os-release'),'boot_id':read('/proc/sys/kernel/random/boot_id'),
 'uptime':read('/proc/uptime'),'memory':read('/proc/meminfo'),
 'root_storage':{'available_bytes':v.f_bavail*v.f_frsize,'total_bytes':v.f_blocks*v.f_frsize}},sort_keys=True))
''',
    'dependencies': '''
import importlib.util,json,shutil
modules={}
for name in ['PIL','numpy','PySide6','PyQt5','tkinter','cv2','pygame','gi']:
 try:
  spec=importlib.util.find_spec(name)
  modules[name]={'present':spec is not None,'origin':spec.origin if spec else None}
 except Exception as e:modules[name]={'present':False,'error':type(e).__name__+': '+str(e)}
print(json.dumps({'modules':modules,'executables':{n:shutil.which(n) for n in ['python3','xrandr','aplay','ffplay','gst-launch-1.0','qmake','pip3','ssh']},'note':'Module discovery only; no Qt/audio backend functional verification.'},sort_keys=True))
''',
    'display': '''
import glob,json,os,re,shutil,subprocess
from pathlib import Path
def read(p):
 try:return Path(p).read_text().strip()
 except OSError:return None
connectors={}
for p in glob.glob('/sys/class/drm/card*-*'):
 if Path(p,'status').exists():connectors[Path(p).name]={n:read(str(Path(p,n))) for n in ['status','enabled','dpms','modes']}
sessions=[]
for p in Path('/proc').iterdir():
 if not p.name.isdigit():continue
 try:
  args=(p/'cmdline').read_bytes().decode(errors='replace').split('\\x00')
  comm=(p/'comm').read_text().strip()
 except OSError:continue
 if comm not in ['Xorg','Xwayland','weston']:continue
 item={'pid':int(p.name),'program':comm,'display':next((a for a in args if re.fullmatch(r':\\d+(?:\\.\\d+)?',a)),None),'authority':None}
 if '-auth' in args:
  i=args.index('-auth')+1
  if i<len(args) and Path(args[i]).is_file():item['authority']=args[i]
 sessions.append(item)
result={'connectors':connectors,'sessions':sessions,'xrandr':None}
candidate=next((s for s in sessions if s['display']),None)
if candidate and shutil.which('xrandr'):
 env=dict(os.environ,DISPLAY=candidate['display'])
 if candidate['authority']:env['XAUTHORITY']=candidate['authority']
 try:
  p=subprocess.run(['xrandr','--current'],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,env=env,timeout=8,text=True)
  result['xrandr']={'exit_code':p.returncode,'output':p.stdout}
 except Exception as e:result['xrandr']={'error':type(e).__name__+': '+str(e)}
print(json.dumps(result,sort_keys=True))
''',
    'audio': '''
import json,shutil,subprocess
from pathlib import Path
result={'alsa_cards':None,'aplay':{},'sound_nodes':[]}
try:result['alsa_cards']=Path('/proc/asound/cards').read_text()
except OSError:pass
if Path('/dev/snd').exists():result['sound_nodes']=sorted(p.name for p in Path('/dev/snd').iterdir())
if shutil.which('aplay'):
 for arg in ['-l','-L']:
  try:
   p=subprocess.run(['aplay',arg],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=8,text=True)
   result['aplay'][arg]={'exit_code':p.returncode,'output':p.stdout}
  except Exception as e:result['aplay'][arg]={'error':type(e).__name__+': '+str(e)}
print(json.dumps(result,sort_keys=True))
''',
    'workloads_and_resources': '''
import json,os,shutil,subprocess
from pathlib import Path
tasks=[]
for p in Path('/proc').iterdir():
 if not p.name.isdigit() or int(p.name)==os.getpid():continue
 try:
  comm=(p/'comm').read_text().strip()
  args=(p/'cmdline').read_bytes().decode(errors='replace').split('\\x00')
 except OSError:continue
 if not any(k in comm.lower() for k in ['python','xorg','weston','dfx','vitis','aura','fpgautil']):continue
 scripts=[a for a in args[1:] if a.endswith('.py') and '\\n' not in a and len(a)<256]
 tasks.append({'pid':int(p.name),'program':comm,'scripts':scripts})
dirs=[]
for base in ['/home/root','/home/ubuntu','/root','/opt','/mnt','/media']:
 root=Path(base)
 if not root.is_dir():continue
 try:children=list(root.iterdir())
 except OSError:continue
 for p in children:
  if p.is_dir() and any(k in p.name.lower() for k in ['aura','avatar','xilan','deliver','kv260']):
   try:names=sorted(x.name for x in p.iterdir())[:60]
   except OSError:names=[]
   dirs.append({'path':str(p),'entries':names})
result={'selected_processes':tasks,'candidate_directories':dirs,'network':None}
if shutil.which('ip'):
 try:
  p=subprocess.run(['ip','-brief','address'],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=5,text=True)
  result['network']={'exit_code':p.returncode,'output':p.stdout}
 except Exception as e:result['network']={'error':type(e).__name__+': '+str(e)}
print(json.dumps(result,sort_keys=True))
''',
    'native_libraries': '''
import json
result={}
try:
 import PIL
 from PIL import Image
 image=Image.new('RGBA',(2,2),(0,0,0,0))
 result['Pillow']={'version':PIL.__version__,'tiny_image_bytes':len(image.tobytes()),'Resampling':hasattr(Image,'Resampling'),'Transform':hasattr(Image,'Transform')}
except Exception as e:result['Pillow']={'error':type(e).__name__+': '+str(e)}
try:
 from PIL import ImageTk
 result['ImageTk']={'import':True}
except Exception as e:result['ImageTk']={'error':type(e).__name__+': '+str(e)}
try:
 import numpy as np
 result['numpy']={'version':np.__version__,'tiny_array_sum':int(np.array([1,2]).sum())}
except Exception as e:result['numpy']={'error':type(e).__name__+': '+str(e)}
try:
 import tkinter
 tcl=tkinter.Tcl()
 result['tkinter']={'tcl_version':str(tcl.call('info','patchlevel')),'TkVersion':tkinter.TkVersion,'window_created':False}
except Exception as e:result['tkinter']={'error':type(e).__name__+': '+str(e)}
try:
 import gi
 gi.require_version('Gtk','3.0')
 from gi.repository import Gtk
 result['Gtk']={'version':[Gtk.MAJOR_VERSION,Gtk.MINOR_VERSION,Gtk.MICRO_VERSION],'initialized':False}
except Exception as e:result['Gtk']={'error':type(e).__name__+': '+str(e)}
try:
 gi.require_version('Gst','1.0')
 from gi.repository import Gst
 result['Gst']={'version':Gst.version_string(),'initialized':False}
except Exception as e:result['Gst']={'error':type(e).__name__+': '+str(e)}
try:
 gi.require_version('GdkPixbuf','2.0')
 from gi.repository import GdkPixbuf
 pixbuf=GdkPixbuf.Pixbuf.new(GdkPixbuf.Colorspace.RGB,True,8,2,2)
 result['GdkPixbuf']={'tiny_image_size':[pixbuf.get_width(),pixbuf.get_height()]}
except Exception as e:result['GdkPixbuf']={'error':type(e).__name__+': '+str(e)}
print(json.dumps(result,sort_keys=True))
''',
    'audio_formats_and_mixer': '''
import json,shutil,subprocess
from pathlib import Path
result={'usb_stream':None,'mixer':None,'gstreamer_elements':{},'pulse_processes':[]}
try:result['usb_stream']=Path('/proc/asound/card2/stream0').read_text()
except OSError:pass
if shutil.which('amixer'):
 try:
  p=subprocess.run(['amixer','-c','MCP01','scontents'],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=5,text=True)
  result['mixer']={'exit_code':p.returncode,'output':p.stdout}
 except Exception as e:result['mixer']={'error':type(e).__name__+': '+str(e)}
if shutil.which('gst-inspect-1.0'):
 for name in ['wavparse','alsasink','pulsesink','playbin']:
  try:
   p=subprocess.run(['gst-inspect-1.0',name],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=5,text=True)
   result['gstreamer_elements'][name]={'exit_code':p.returncode,'available':p.returncode==0,'output_sha256':__import__('hashlib').sha256(p.stdout.encode()).hexdigest()}
  except Exception as e:result['gstreamer_elements'][name]={'error':type(e).__name__+': '+str(e)}
for p in Path('/proc').iterdir():
 if not p.name.isdigit():continue
 try:comm=(p/'comm').read_text().strip()
 except OSError:continue
 if comm in ['pulseaudio','pipewire']:result['pulse_processes'].append({'pid':int(p.name),'program':comm})
print(json.dumps(result,sort_keys=True))
''',
    'fonts_and_runtime_paths': '''
import json,shutil,subprocess
from pathlib import Path
paths=['/home/root/aura','/home/root/deliverables','/home/ubuntu/aura','/home/ubuntu/deliverables','/opt/aura']
result={'expected_paths':{p:Path(p).exists() for p in paths},'chinese_fonts':None}
if shutil.which('fc-list'):
 try:
  p=subprocess.run(['fc-list',':lang=zh','file','family'],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=5,text=True)
  result['chinese_fonts']={'exit_code':p.returncode,'entries':p.stdout.splitlines()[:30]}
 except Exception as e:result['chinese_fonts']={'error':type(e).__name__+': '+str(e)}
print(json.dumps(result,sort_keys=True))
''',
}


def utc():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def command_for(source):
    source = textwrap.dedent(source).strip() + '\n'
    ast.parse(source)
    compressed = base64.b64encode(gzip.compress(source.encode(), mtime=0)).decode()
    code = 'import base64,gzip;exec(gzip.decompress(base64.b64decode(' + repr(compressed) + ')))'
    command = 'python3 -B -c ' + shlex.quote(code)
    # The framed transport base64-encodes this command. Its fixed wrapper is <900 bytes.
    if len(base64.b64encode(command.encode())) + 900 > 3800:
        raise ValueError('Probe exceeds conservative UART wire size')
    return command


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--validate', action='store_true', help='Validate probes locally without opening the UART')
    parser.add_argument('--only', nargs='+', choices=tuple(PROBES), help='Run only the named read-only probes')
    args = parser.parse_args()
    names = args.only or tuple(PROBES)
    commands = {name: command_for(PROBES[name]) for name in names}
    if args.validate:
        print(json.dumps({'validated_probes':list(commands),'no_uart_access':True}))
        return 0
    spec = importlib.util.spec_from_file_location('reviewed_uart_transport', str(TRANSPORT))
    transport = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(transport)
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')
    out = ROOT / 'evidence' / (stamp + '-board-environment')
    out.mkdir(parents=True)
    status = {'started_utc':utc(),'port':transport.PORT,'read_only_board_probes':True,
              'probe_script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              'transport_sha256':hashlib.sha256(TRANSPORT.read_bytes()).hexdigest(),
              'complete':False,'results':[],'evidence_directory':str(out)}
    (out/'commands.json').write_text(json.dumps(commands,indent=2)+'\n')
    uart = None
    with (out/'serial.raw').open('xb') as raw:
        try:
            uart = transport.UART(raw)
            uart.connect()
            status['root_shell_confirmed'] = True
            print(json.dumps({'root_shell_confirmed':True,'evidence':str(out)}),flush=True)
            for index,(name,command) in enumerate(commands.items()):
                rc,data,sha = uart.command(command,'AE%03d'%index,40)
                (out/(name+'.output')).write_bytes(data)
                result = {'id':name,'exit_code':rc,'bytes':len(data),'output_sha256':sha}
                if rc == 0:
                    payload = json.loads(data)
                    (out/(name+'.json')).write_text(json.dumps(payload,indent=2,ensure_ascii=False)+'\n')
                status['results'].append(result)
                (out/'status.json').write_text(json.dumps(status,indent=2)+'\n')
                print(json.dumps(result),flush=True)
                if rc != 0:
                    raise RuntimeError('Read-only probe failed: '+name)
            status['complete'] = True
        except Exception as exc:
            status['error'] = type(exc).__name__+': '+str(exc)
            print(json.dumps({'error':status['error']}),flush=True)
        finally:
            if uart is not None:
                try:status['console_echo_restored'] = uart.close()
                except Exception as exc:status['console_close_error'] = str(exc)
    status['finished_utc'] = utc()
    (out/'status.json').write_text(json.dumps(status,indent=2)+'\n')
    print(json.dumps({'complete':status['complete'],'evidence':str(out),
                      'console_echo_restored':status.get('console_echo_restored')}),flush=True)
    return 0 if status['complete'] and status.get('console_echo_restored') else 1


if __name__ == '__main__':
    sys.exit(main())
