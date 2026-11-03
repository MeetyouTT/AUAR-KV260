#!/usr/bin/env python3
"""Read-only KV260 USB/HID/kernel/X11 diagnosis over the reviewed UART."""
import argparse
import datetime
import gzip
import hashlib
import importlib.util
import json
from pathlib import Path
import shlex
import base64

ROOT = Path(__file__).resolve().parent
TRANSPORT = Path('/home/ghmd/kv260-dfx-state-boardtest-20261004/scripts/uart_phase.py')
PROBES = {
    'runtime_inventory': r'''
import hashlib,json,os,subprocess
from pathlib import Path
root=Path('/home/root/aura-avatar-gtk-stage/runtime-1a8677ce-20261009')
result={'boot_id':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),'files':{},'processes':[],'display':{}}
for name in ['launch.json','avatar_user_settings.json','stage.log']:
 p=root/name
 if p.exists():result['files'][name]=p.read_text(errors='replace')[-3000:]
for p in Path('/proc').iterdir():
 if not p.name.isdigit():continue
 try:
  comm=(p/'comm').read_text().strip()
  if comm not in ['python3','Xorg','dfx-mgrd']:continue
  args=(p/'cmdline').read_bytes().decode(errors='replace').split(chr(0))
  scripts=[x for x in args if x.endswith('.py') and len(x)<250 and chr(10) not in x]
  result['processes'].append({'pid':int(p.name),'comm':comm,'scripts':scripts})
 except OSError:pass
env=dict(os.environ,DISPLAY=':0')
for cmd in [['xrandr','--verbose'],['xset','q']]:
 p=subprocess.run(cmd,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=6)
 result['display'][' '.join(cmd)]={'exit_code':p.returncode,'output':p.stdout}
for p in Path('/sys/class/drm').glob('card*-DP-1/edid'):
 data=p.read_bytes();result['display'][str(p)]={'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()}
print(json.dumps(result,ensure_ascii=False))
''',
    'post_load': r'''
import json,os,subprocess,urllib.request
from pathlib import Path
env=dict(os.environ,DISPLAY=':0')
result={'module_loaded':Path('/sys/module/hid_multitouch').exists(),'driver_registered':Path('/sys/bus/hid/drivers/hid-multitouch').exists(),'usb':[],'touch_devices':[]}
for d in sorted(Path('/sys/bus/usb/devices').iterdir()):
 if (d/'idVendor').exists():result['usb'].append({'path':d.name,'vendor':(d/'idVendor').read_text().strip(),'product_id':(d/'idProduct').read_text().strip(),'product':(d/'product').read_text().strip() if (d/'product').exists() else ''})
for e in Path('/sys/class/input').glob('event*'):
 d=e/'device';props=(d/'properties').read_text().strip().split()
 if props and int(props[-1],16)&2:result['touch_devices'].append({'event':e.name,'name':(d/'name').read_text().strip()})
with urllib.request.urlopen('http://127.0.0.1:8783/api/state',timeout=5) as response:ui=json.load(response)
result['ui']={k:ui.get(k) for k in ['phase','state','error','ui_page','ui_settings','touch_devices']}
result['stage_errors']=[s for s in Path('/home/root/aura-avatar-gtk-stage/runtime-1a8677ce-20261009/stage.log').read_text().splitlines() if 'STAGE ERROR' in s or 'Traceback' in s][-20:]
result['vision_process_alive']=Path('/proc/16981').exists()
result['boot_id']=Path('/proc/sys/kernel/random/boot_id').read_text().strip()
p=subprocess.run(['xinput','list','--short'],env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=5)
result['xinput']={'exit_code':p.returncode,'output':p.stdout}
p=subprocess.run(['dmesg'],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=5)
result['multitouch_kernel_log']=[s for s in p.stdout.splitlines() if 'multitouch' in s.lower() or 'unknown symbol' in s.lower() or 'disagrees about version' in s.lower()][-20:]
print(json.dumps(result,ensure_ascii=False))
''',
    'symbol_visibility': r'''
import gzip,json
from pathlib import Path
names={line.split()[2] for line in Path('/proc/kallsyms').read_text().splitlines() if len(line.split())>=3}
required=set('___ratelimit __hid_register_driver __hid_request __stack_chk_fail _dev_err _dev_warn _find_first_bit _find_next_bit _printk del_timer del_timer_sync devm_kfree devm_kmalloc hid_alloc_report_buf hid_hw_start hid_hw_stop hid_open_report hid_report_raw_event hid_unregister_driver hidinput_calc_abs_res init_timer_key input_alloc_absinfo input_event input_mt_get_slot_by_key input_mt_init_slots input_mt_report_slot_state input_mt_sync_frame input_set_abs_params input_set_capability jiffies jiffies_to_usecs kfree kstrtoull mod_timer sprintf strlen sysfs_create_group sysfs_remove_group'.split())
config=gzip.open('/proc/config.gz','rt').read()
print(json.dumps({'names_count':len(names),'ksymtab_count':sum(n.startswith('__ksymtab_') for n in names),'required_count':len(required),'missing_required_names':sorted(required-names),'kallsyms_config':[s for s in config.splitlines() if 'CONFIG_KALLSYMS' in s]}))
''',
    'kernel_abi': r'''
import base64,gzip,hashlib,json,os,subprocess
from pathlib import Path
config=gzip.open('/proc/config.gz','rb').read()
result={'release':os.uname().release,'version':Path('/proc/version').read_text().strip(),
 'config_sha256':hashlib.sha256(config).hexdigest(),'config_gzip_base64':base64.b64encode(gzip.compress(config)).decode(),
 'zocl_vermagic':subprocess.run(['modinfo','-F','vermagic','zocl'],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=5).stdout.strip()}
print(json.dumps(result))
''',
    'usb_and_hid': r'''
import json,os,subprocess,shutil
from pathlib import Path
def read(p):
 try:return Path(p).read_text(errors='replace').strip()
 except OSError:return None
devices=[]
for p in sorted(Path('/sys/bus/usb/devices').iterdir()):
 if not (p/'idVendor').exists():continue
 row={'path':p.name,'fields':{k:read(p/k) for k in ['idVendor','idProduct','manufacturer','product','bDeviceClass','bConfigurationValue','authorized','speed','busnum','devnum','power/control','power/runtime_status']},'interfaces':[]}
 for d in sorted(p.glob(p.name+':*')):
  row['interfaces'].append({'name':d.name,'class':read(d/'bInterfaceClass'),'subclass':read(d/'bInterfaceSubClass'),'protocol':read(d/'bInterfaceProtocol'),'driver':(d/'driver').resolve().name if (d/'driver').exists() else None,'modalias':read(d/'modalias')})
 devices.append(row)
hid=[]
for d in sorted(Path('/sys/bus/hid/devices').glob('*')):
 hid.append({'id':d.name,'driver':(d/'driver').resolve().name if (d/'driver').exists() else None,'uevent':read(d/'uevent'),'report_descriptor_bytes':(d/'report_descriptor').stat().st_size if (d/'report_descriptor').exists() else None})
inputs=[]
for p in sorted(Path('/sys/class/input').glob('event*')):
 d=p/'device';inputs.append({'event':p.name,**{k:read(d/k) for k in ['name','properties','capabilities/ev','capabilities/abs','phys','id/vendor','id/product']}})
result={'boot_id':read('/proc/sys/kernel/random/boot_id'),'usb':devices,'hid':hid,'inputs':inputs,'usb_tree':None}
if shutil.which('lsusb'):
 p=subprocess.run(['lsusb','-t'],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=5);result['usb_tree']={'exit_code':p.returncode,'output':p.stdout}
print(json.dumps(result,ensure_ascii=False))
''',
    'kernel_and_x11': r'''
import json,os,gzip,re,subprocess,shutil
from pathlib import Path
def read(p):
 try:return Path(p).read_text(errors='replace').strip()
 except OSError:return None
release=os.uname().release;config=None;config_source=None
for path in ['/proc/config.gz','/boot/config-'+release,'/lib/modules/'+release+'/build/.config']:
 try:
  config=gzip.open(path,'rt').read() if path.endswith('.gz') else Path(path).read_text();config_source=path;break
 except OSError:pass
keys=['CONFIG_INPUT','CONFIG_INPUT_EVDEV','CONFIG_HID','CONFIG_HID_GENERIC','CONFIG_HID_MULTITOUCH','CONFIG_USB_HID','CONFIG_USB_SUPPORT','CONFIG_USB','CONFIG_IKCONFIG','CONFIG_IKCONFIG_PROC']
kernel_config={}
if config:
 for key in keys:
  match=re.search(r'(?m)^'+key+r'=(.*)$',config);kernel_config[key]=match.group(1) if match else ('not set' if '# '+key+' is not set' in config else 'not found')
mods={}
for name in ['hid','hid_generic','hid_multitouch','usbhid']:
 p=Path('/sys/module')/name;mods[name]={'present':p.exists(),'initstate':read(p/'initstate'),'refcnt':read(p/'refcnt')}
result={'kernel':release,'config_source':config_source,'kernel_config':kernel_config,'modules':mods,'tools':{n:shutil.which(n) for n in ['xinput','evtest','libinput','modprobe','modinfo']},'commands':{},'xorg_input_log':[]}
env=dict(os.environ,DISPLAY=':0')
for args in [['xinput','list','--long'],['xrandr','--current'],['modprobe','-n','-v','hid-multitouch'],['modinfo','hid-multitouch']]:
 if not shutil.which(args[0]):continue
 p=subprocess.run(args,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,env=env,timeout=5);result['commands'][' '.join(args)]={'exit_code':p.returncode,'output':p.stdout[-12000:]}
for p in [Path('/var/log/Xorg.0.log'),Path('/home/root/.local/share/xorg/Xorg.0.log')]:
 if not p.exists():continue
 lines=[s for s in p.read_text(errors='replace').splitlines() if any(k in s.lower() for k in ['libinput','evdev','touch','waveshare','input device','using input','ignoring device'])]
 result['xorg_input_log'].append({'path':str(p),'lines':lines[-75:]})
p=subprocess.run(['dmesg'],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=5)
result['usb_hid_kernel_log']=[s for s in p.stdout.splitlines() if re.search(r'usb|hid|touch',s,re.I)][-85:]
result['xorg_drivers']=[p.name for p in Path('/usr/lib/xorg/modules/input').glob('*')]
print(json.dumps(result,ensure_ascii=False))
''',
}


def utc():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def command(source):
    compile(source, '<read-only touch probe>', 'exec')
    payload = base64.b64encode(gzip.compress(source.encode(), mtime=0)).decode()
    result = 'python3 -B -c ' + shlex.quote('import base64,gzip;exec(gzip.decompress(base64.b64decode(' + repr(payload) + ')))')
    if len(result.encode()) > 3800:
        raise RuntimeError('UART command limit')
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--validate', action='store_true')
    parser.add_argument('--only', nargs='+', choices=tuple(PROBES))
    args = parser.parse_args()
    names = args.only or ('usb_and_hid', 'kernel_and_x11')
    commands = {k: command(PROBES[k]) for k in names}
    if args.validate:
        print(json.dumps({'probes': list(commands), 'uart_accessed': False,
                          'wire_lengths': {k: len(v.encode()) for k, v in commands.items()}}))
        return 0
    spec = importlib.util.spec_from_file_location('reviewed_uart', str(TRANSPORT))
    transport = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(transport)
    out = ROOT/'evidence'/datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ-inspect')
    out.mkdir(parents=True)
    status = {'started_utc': utc(), 'read_only': True, 'complete': False, 'results': [],
              'script_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              'transport_sha256': hashlib.sha256(TRANSPORT.read_bytes()).hexdigest()}
    (out/'commands.json').write_text(json.dumps(commands, indent=2)+'\n')
    uart = None
    with (out/'serial.raw').open('xb') as raw:
        try:
            uart = transport.UART(raw)
            uart.connect()
            print(json.dumps({'root_shell_confirmed': True, 'evidence': str(out)}), flush=True)
            for index, (name, wire) in enumerate(commands.items()):
                rc, data, digest = uart.command(wire, 'WT%03d'%index, 40)
                (out/(name+'.output')).write_bytes(data)
                row = {'name': name, 'exit_code': rc, 'bytes': len(data), 'sha256': digest}
                status['results'].append(row)
                print(json.dumps(row), flush=True)
                if rc:
                    raise RuntimeError(name+' failed')
                (out/(name+'.json')).write_text(json.dumps(json.loads(data), ensure_ascii=False, indent=2)+'\n')
            status['complete'] = True
        except Exception as exc:
            status['error'] = str(exc)
        finally:
            if uart is not None:
                status['console_echo_restored'] = uart.close()
    status['finished_utc'] = utc()
    (out/'status.json').write_text(json.dumps(status, indent=2)+'\n')
    print(json.dumps({'evidence': str(out), **status}), flush=True)
    return 0 if status['complete'] and status.get('console_echo_restored') else 1


if __name__ == '__main__':
    raise SystemExit(main())
