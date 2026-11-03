#!/usr/bin/env python3
"""Transfer and load one pinned upstream HID MT module; no reboot or forced load."""
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
MODULE = ROOT/'module-build/driver/hid-multitouch.ko'
SHA = 'fce568b070bbc0e9210bc6417b39e1c57637d9d24d9fdebc4cb913603505417b'
SIZE = 34944
LIVE_CONFIG = '3d97bf208930f5696093d2d1999b4a0b16bcb121c97d70ca286bb8d4986e81ef'
DEST = '/home/root/aura-waveshare-touch-20261009/module-fce568b070bbc0e9'
RELEASE = '5.15.36-xilinx-v2022.2'
VERMAGIC = RELEASE+' SMP mod_unload aarch64'


def wire(source):
    compile(source, '<pinned HID MT load>', 'exec')
    encoded = base64.b64encode(gzip.compress(source.encode(), mtime=0)).decode()
    result = 'python3 -B -c '+shlex.quote('import base64,gzip;exec(gzip.decompress(base64.b64decode('+repr(encoded)+')))')
    assert len(result.encode()) <= 3800
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--validate', action='store_true')
    parser.add_argument('--resume-staged', action='store_true')
    args = parser.parse_args()
    payload = MODULE.read_bytes()
    assert len(payload) == SIZE and hashlib.sha256(payload).hexdigest() == SHA
    manifest = json.loads((ROOT/'module_build_validation.json').read_text())
    assert manifest['complete'] and manifest['vermagic'] == VERMAGIC
    symbols = sorted({line.split()[-1] for line in (ROOT/'module-build/logs/undefined.log').read_text().splitlines()})
    compressed = gzip.compress(payload, mtime=0)
    prelude = 'import base64,gzip,hashlib,json,os,subprocess,time\nfrom pathlib import Path\nroot=Path('+repr(DEST)+')\n'
    commands = [('prepare', prelude+'''assert os.uname().release == RELEASE
assert hashlib.sha256(gzip.open('/proc/config.gz','rb').read()).hexdigest() == LIVE_CONFIG
assert not Path('/sys/module/hid_multitouch').exists()
root.mkdir(parents=True,exist_ok=False)
(root/'hid-multitouch.ko.gz.part').open('xb').close()
'''.replace('RELEASE', repr(RELEASE)).replace('LIVE_CONFIG', repr(LIVE_CONFIG)))]
    for pos in range(0, len(compressed), 768):
        piece = base64.b64encode(compressed[pos:pos+768]).decode()
        code = prelude+"p=root/'hid-multitouch.ko.gz.part'\nassert p.stat().st_size=="+str(pos)+"\nwith p.open('ab') as f:\n f.write(base64.b64decode("+repr(piece)+"));f.flush();os.fsync(f.fileno())\n"
        commands.append(('chunk-%03d'%(pos//768), code))
    load = prelude+'''
raw=gzip.decompress((root/'hid-multitouch.ko.gz.part').read_bytes())
assert len(raw)==SIZE and hashlib.sha256(raw).hexdigest()==SHA
target=root/'hid-multitouch.ko'
assert root.is_dir() and not root.is_symlink() and not target.is_symlink()
if not target.exists():
 with target.open('xb') as f:f.write(raw);f.flush();os.fsync(f.fileno())
assert hashlib.sha256(target.read_bytes()).hexdigest()==SHA
assert os.uname().release==RELEASE
assert hashlib.sha256(gzip.open('/proc/config.gz','rb').read()).hexdigest()==LIVE_CONFIG
p=subprocess.run(['modinfo','-F','vermagic',str(target)],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=5)
assert p.returncode==0 and p.stdout.strip()==VERMAGIC,p.stdout
names={line.split()[2] for line in Path('/proc/kallsyms').read_text().splitlines() if len(line.split())>=3}
required=set(SYMBOLS)
config=gzip.open('/proc/config.gz','rt').read()
assert '# CONFIG_KALLSYMS_ALL is not set' in config
# This kernel omits __ksymtab metadata and data symbols from kallsyms.
# The prepared System.map identifies jiffies as D; all 37 function names must exist.
assert required-names=={'jiffies'},sorted(required-names)
assert not Path('/sys/module/hid_multitouch').exists()
before_taint=Path('/proc/sys/kernel/tainted').read_text().strip()
p=subprocess.run(['insmod',str(target)],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=10)
assert p.returncode==0,p.stdout
assert Path('/sys/module/hid_multitouch').exists()
assert Path('/sys/bus/hid/drivers/hid-multitouch').exists()
time.sleep(.5)
bindings={x.name:(x/'driver').resolve().name for x in Path('/sys/bus/hid/devices').glob('*') if (x/'driver').exists()}
devices=[]
for e in Path('/sys/class/input').glob('event*'):
 d=e/'device';props=(d/'properties').read_text().strip().split()
 if props and int(props[-1],16)&2:devices.append({'event':e.name,'name':(d/'name').read_text().strip()})
processes=[]
result={'complete':True,'module':str(target),'bytes':SIZE,'sha256':SHA,'vermagic':VERMAGIC,'config_sha256':LIVE_CONFIG,'visible_required_function_names':len(required)-1,'kernel_export_table_visible':False,'kernel_loader_resolved_symbols':len(required),'module_loaded':True,'driver_registered':True,'touch_devices':devices,'hid_bindings':bindings,'existing_processes':processes,'taint_before':before_taint,'taint_after':Path('/proc/sys/kernel/tainted').read_text().strip(),'boot_id':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),'persistent_install':False,'forced_load':False}
record=root/('LOADED_'+result['boot_id']+'.json')
with record.open('x') as f:json.dump(result,f,indent=2);f.flush();os.fsync(f.fileno())
print(json.dumps(result))
'''
    replacements = {'SIZE': repr(SIZE), 'SHA': repr(SHA), 'RELEASE': repr(RELEASE),
                    'LIVE_CONFIG': repr(LIVE_CONFIG), 'VERMAGIC': repr(VERMAGIC), 'SYMBOLS': repr(symbols)}
    for key, value in replacements.items():
        load = load.replace(key, value)
    commands.append(('verified-load', load))
    if args.resume_staged:
        commands = commands[-1:]
    commands = [(name, wire(source)) for name, source in commands]
    if args.validate:
        print(json.dumps({'commands':len(commands),'module_bytes':SIZE,'compressed_bytes':len(compressed),
                          'sha256':SHA,'max_wire_bytes':max(len(s.encode()) for _,s in commands),'board_accessed':False}))
        return 0
    spec = importlib.util.spec_from_file_location('reviewed_uart',str(TRANSPORT))
    transport = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(transport)
    out = ROOT/'evidence'/datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ-module-load')
    out.mkdir(parents=True)
    status = {'complete':False,'module_sha256':SHA,'destination':DEST,'commands':[]}
    uart = None
    with (out/'serial.raw').open('xb') as raw:
        try:
            uart = transport.UART(raw)
            uart.connect()
            print(json.dumps({'root_shell_confirmed':True,'evidence':str(out)}),flush=True)
            for index,(name,command) in enumerate(commands):
                rc,data,digest = uart.command(command,'WL%03d'%index,40)
                (out/(name+'.output')).write_bytes(data)
                status['commands'].append({'name':name,'exit_code':rc,'bytes':len(data),'sha256':digest,'command':command})
                if rc:
                    raise RuntimeError(name+': '+data.decode(errors='replace')[-1500:])
                if name=='verified-load':
                    status['result']=json.loads(data)
                    print(data.decode(),flush=True)
                elif index%4==0:
                    print(json.dumps({'step':name,'completed':index+1,'total':len(commands)}),flush=True)
            status['complete']=True
        except Exception as exc:
            status['error']=str(exc)
        finally:
            if uart is not None:
                status['console_echo_restored']=uart.close()
    (out/'status.json').write_text(json.dumps(status,indent=2)+'\n')
    print(json.dumps({k:v for k,v in status.items() if k!='commands'}),flush=True)
    return 0 if status['complete'] and status.get('console_echo_restored') else 1


if __name__=='__main__':
    raise SystemExit(main())
