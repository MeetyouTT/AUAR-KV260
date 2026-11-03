#!/usr/bin/env python3
"""Stage the reviewed candidate and bind it for the next boot without restarting AURA."""
import base64
import datetime
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent
TRANSPORT = Path('/home/ghmd/kv260-dfx-state-boardtest-20261004/scripts/uart_phase.py')
STARTUP_TOOL = Path('/home/ghmd/aura-board-ui-autostart-20261009/manage_startup.py')
RELEASE = '/home/root/aura-avatar-startup-speed-20261029'
STAGE = '/tmp/aura-avatar-startup-speed-20261029.bundle.part'
BOOT_ID = '605eaf50-c66a-4559-bfc9-5ae177e0f305'
ACTIVE_CONFIG = '/home/root/aura-boundary-nav-20261029/gui-page-sync-v2/startup/config.json'
ACTIVE_LAUNCHER = '/home/root/aura-boundary-nav-20261029/gui-page-sync-v2/startup/launcher.py'
SERVICE = 'aura-avatar-ui.service'


def transport_module():
    spec = importlib.util.spec_from_file_location('reviewed_uart', str(TRANSPORT))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def wire(source):
    spec = importlib.util.spec_from_file_location('startup_tool', str(STARTUP_TOOL))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.wire(source)


manifest = json.loads((ROOT/'release_manifest.json').read_text(encoding='utf-8'))
files = manifest['files']
dropin = manifest['dropin_path']
bundle = (ROOT/'candidate_bundle.gz').read_bytes()
bundle_text = base64.b64encode(bundle).decode('ascii')
bundle_sha = hashlib.sha256(bundle_text.encode('ascii')).hexdigest()

guard_script = r'''
import hashlib,json,subprocess
from pathlib import Path
def run(args):
 p=subprocess.run(args,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=18)
 assert p.returncode==0,(args,p.stdout[-1200:])
 return p.stdout
def props(unit):
 out=run(['systemctl','show',unit,'-p','ActiveState','-p','MainPID','-p','ExecStart','-p','DropInPaths','-p','UnitFileState'])
 return dict(line.split('=',1) for line in out.splitlines() if '=' in line)
boot=Path('/proc/sys/kernel/random/boot_id').read_text().strip()
assert boot==EXPECTED_BOOT,(boot,EXPECTED_BOOT)
p=props(SERVICE)
assert p.get('ActiveState')=='active',p
assert p.get('MainPID')=='1296',p
assert ACTIVE_LAUNCHER in p.get('ExecStart',''),p
assert p.get('UnitFileState')=='enabled',p
assert hashlib.sha256(Path(ACTIVE_CONFIG).read_bytes()).hexdigest()==EXPECTED_CONFIG_SHA
assert not Path(RELEASE).exists(),RELEASE
assert not Path(DROPIN).exists(),DROPIN
print(json.dumps({'boot_id':boot,'service':p,'active_config_sha256':EXPECTED_CONFIG_SHA,'candidate_path_unused':True,'dropin_path_unused':True}))
'''.replace('EXPECTED_BOOT', repr(BOOT_ID)).replace('SERVICE', repr(SERVICE)).replace(
    'ACTIVE_LAUNCHER', repr(ACTIVE_LAUNCHER)).replace('ACTIVE_CONFIG', repr(ACTIVE_CONFIG)).replace(
    'EXPECTED_CONFIG_SHA', repr(manifest['active_config_sha256'])).replace('RELEASE', repr(RELEASE)).replace(
    'DROPIN', repr(dropin))

offset_script = r'''
import hashlib,json
from pathlib import Path
p=Path(STAGE)
if p.exists():assert not p.is_symlink()
d=p.read_bytes() if p.exists() else b''
print(json.dumps({'offset':len(d),'sha256':hashlib.sha256(d).hexdigest()}))
'''.replace('STAGE', repr(STAGE))

chunk_commands = []
for offset in range(0, len(bundle_text), 1200):
    value = bundle_text[offset:offset+1200]
    source = r'''
import hashlib,json,os
from pathlib import Path
p=Path(STAGE);assert not p.is_symlink()
offset=OFFSET
d=p.read_bytes() if p.exists() else b''
assert len(d)==offset,(len(d),offset)
with p.open('ab') as f:f.write(VALUE);f.flush();os.fsync(f.fileno())
d=p.read_bytes()
print(json.dumps({'offset':len(d),'sha256':hashlib.sha256(d).hexdigest()}))
'''.replace('STAGE', repr(STAGE)).replace('OFFSET', str(offset)).replace('VALUE', repr(value.encode('ascii')))
    chunk_commands.append((offset, wire(source)))

finish_script = r'''
import base64,gzip,hashlib,json,os
from pathlib import Path
p=Path(STAGE);d=p.read_bytes()
assert hashlib.sha256(d).hexdigest()==BUNDLE_SHA
payload=json.loads(gzip.decompress(base64.b64decode(d)))
assert set(payload)=={'launcher.py','config.json','dropin.conf'}
root=Path(RELEASE);assert not root.exists();root.mkdir(mode=0o755)
result={}
for name,record in payload.items():
 raw=base64.b64decode(record['base64'],validate=True)
 assert len(raw)==record['bytes'] and hashlib.sha256(raw).hexdigest()==record['sha256']
 target=root/name
 with target.open('xb') as f:f.write(raw);f.flush();os.fsync(f.fileno())
 result[name]={'bytes':len(raw),'sha256':hashlib.sha256(target.read_bytes()).hexdigest()}
print(json.dumps({'release':str(root),'files':result}))
'''.replace('STAGE', repr(STAGE)).replace('BUNDLE_SHA', repr(bundle_sha)).replace('RELEASE', repr(RELEASE))

preflight_script = r'''
import hashlib,json,subprocess
from pathlib import Path
root=Path(RELEASE)
expected=FILES
for name,record in expected.items():
 p=root/name;assert not p.is_symlink() and p.stat().st_size==record['bytes']
 assert hashlib.sha256(p.read_bytes()).hexdigest()==record['sha256'],name
p=subprocess.run(['/usr/bin/python3','-B',str(root/'launcher.py'),'--config',str(root/'config.json'),'--preflight'],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=90)
assert p.returncode==0,p.stdout[-5000:]
print(json.dumps({'preflight':'PASS','output':p.stdout.strip(),'files':expected}))
'''.replace('RELEASE', repr(RELEASE)).replace('FILES', repr(files))

install_script = r'''
import hashlib,json,os,subprocess
from pathlib import Path
def run(args):
 p=subprocess.run(args,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=30)
 assert p.returncode==0,(args,p.stdout[-1600:])
 return p.stdout
def props():
 out=run(['systemctl','show',SERVICE,'-p','ActiveState','-p','MainPID','-p','ExecStart','-p','DropInPaths','-p','UnitFileState'])
 return dict(line.split('=',1) for line in out.splitlines() if '=' in line)
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==EXPECTED_BOOT
before=props();assert before.get('ActiveState')=='active' and before.get('MainPID')=='1296',before
assert ACTIVE_LAUNCHER in before.get('ExecStart','')
assert hashlib.sha256(Path(ACTIVE_CONFIG).read_bytes()).hexdigest()==EXPECTED_CONFIG_SHA
root=Path(RELEASE);assert root.is_dir()
expected=FILES
for name,record in expected.items():
 p=root/name;assert not p.is_symlink() and p.stat().st_size==record['bytes']
 assert hashlib.sha256(p.read_bytes()).hexdigest()==record['sha256'],name
dropin=Path(DROPIN);assert not dropin.exists() and not dropin.is_symlink()
existing=[Path(x) for x in before.get('DropInPaths','').split()]
assert all(dropin.name>p.name for p in existing),[p.name for p in existing]
data=(root/'dropin.conf').read_bytes();assert hashlib.sha256(data).hexdigest()==DROPIN_SHA
created=False
try:
 with dropin.open('xb') as f:f.write(data);f.flush();os.fsync(f.fileno())
 created=True
 run(['systemctl','daemon-reload'])
 after=props()
 assert after.get('ActiveState')=='active' and after.get('MainPID')==before['MainPID'],after
 assert after.get('UnitFileState')=='enabled',after
 assert str(dropin) in after.get('DropInPaths',''),after
 assert after.get('DropInPaths','').split()[-1]==str(dropin),after
 assert str(root/'launcher.py') in after.get('ExecStart',''),after
 launch=json.loads((Path(CONFIG_RUNTIME)/'launch.json').read_text())
 child=Path('/proc')/str(launch['pid'])
 assert child.exists() and b'board_avatar_pan.py' in (child/'cmdline').read_bytes(),launch
 print(json.dumps({'installed_for_next_start':True,'service_restart_requested':False,'reboot_requested':False,'before':before,'after':after,'current_supervisor_pid_unchanged':True,'current_gui_pid':launch['pid'],'dropin_sha256':DROPIN_SHA,'dropin_order_last':True}))
except Exception:
 if created and dropin.exists() and hashlib.sha256(dropin.read_bytes()).hexdigest()==DROPIN_SHA:
  dropin.unlink();run(['systemctl','daemon-reload'])
 raise
'''.replace('SERVICE', repr(SERVICE)).replace('EXPECTED_BOOT', repr(BOOT_ID)).replace(
    'ACTIVE_LAUNCHER', repr(ACTIVE_LAUNCHER)).replace('ACTIVE_CONFIG', repr(ACTIVE_CONFIG)).replace(
    'EXPECTED_CONFIG_SHA', repr(manifest['active_config_sha256'])).replace('RELEASE', repr(RELEASE)).replace(
    'FILES', repr(files)).replace('DROPIN_SHA', repr(files['dropin.conf']['sha256'])).replace('DROPIN', repr(dropin)).replace(
    'CONFIG_RUNTIME', repr('/home/root/aura-boundary-nav-20261029/gui-page-sync-v2/runtime'))

commands = {
    'guard': wire(guard_script),
    'offset': wire(offset_script),
    'finish': wire(finish_script),
    'preflight': wire(preflight_script),
    'install': wire(install_script),
}
assert all(len(value.encode('utf-8')) <= 3800 for value in commands.values())
if '--validate-only' in sys.argv[1:]:
    print(json.dumps({'validated_remote_command_bytes': {name: len(value.encode('utf-8'))
                                                         for name, value in commands.items()},
                      'chunk_count': len(chunk_commands), 'uart_opened': False,
                      'board_accessed': False}, indent=2))
    raise SystemExit(0)

evidence = ROOT/'evidence'/datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ-nextboot-install')
evidence.mkdir(parents=True, exist_ok=False)
status = {'phase': 'nextboot-install', 'complete': False, 'commands': [], 'bundle_sha256': bundle_sha}
uart = None
try:
    with (evidence/'serial.raw').open('xb') as raw:
        uart = transport_module().UART(raw)
        uart.connect()

        def send(name, command):
            sequence = 'AS'+str(len(status['commands'])+1).zfill(3)
            rc, body, digest = uart.command(command, sequence, 110)
            output = evidence/(sequence+'-'+name+'.output')
            output.write_bytes(body)
            record = {'sequence': sequence, 'name': name, 'exit_code': rc,
                      'bytes': len(body), 'sha256': digest, 'output': output.name}
            status['commands'].append(record)
            if rc:
                raise RuntimeError(name+': '+body.decode(errors='replace')[-3000:])
            parsed = json.loads(body)
            output.with_suffix('.json').write_text(json.dumps(parsed, ensure_ascii=False, indent=2)+'\n',
                                                   encoding='utf-8')
            return parsed

        guard = send('guard', commands['guard'])
        offset = send('offset', commands['offset'])
        start = offset['offset']
        assert 0 <= start <= len(bundle_text)
        assert hashlib.sha256(bundle_text[:start].encode('ascii')).hexdigest() == offset['sha256']
        assert start == len(bundle_text) or start % 1200 == 0
        for chunk_offset, command in chunk_commands:
            if chunk_offset < start:
                continue
            chunk = send('chunk-'+str(chunk_offset), command)
            end = min(chunk_offset+1200, len(bundle_text))
            assert chunk['offset'] == end
            assert chunk['sha256'] == hashlib.sha256(bundle_text[:end].encode('ascii')).hexdigest()
        staged = send('finish', commands['finish'])
        checked = send('preflight', commands['preflight'])
        installed = send('install', commands['install'])
        status.update(complete=True, guard=guard, staged=staged, preflight=checked, installed=installed)
except Exception as exc:
    status['error'] = str(exc)
finally:
    if uart is not None:
        try:
            status['console_echo_restored'] = uart.close()
        except Exception as exc:
            status['console_echo_error'] = str(exc)
(evidence/'status.json').write_text(json.dumps(status, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
print(json.dumps(status, ensure_ascii=False, indent=2))
raise SystemExit(0 if status.get('complete') and status.get('console_echo_restored') else 1)
