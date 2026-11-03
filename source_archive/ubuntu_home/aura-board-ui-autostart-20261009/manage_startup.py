#!/usr/bin/env python3
"""Stage, install and verify the owned UI service over the reviewed UART."""
import argparse
import base64
import datetime
import gzip
import hashlib
import importlib.util
import json
from pathlib import Path
import shlex
from functools import lru_cache

ROOT = Path(__file__).resolve().parent
TRANSPORT = Path('/home/ghmd/kv260-dfx-state-boardtest-20261004/scripts/uart_phase.py')


@lru_cache(maxsize=1)
def transport_module():
    spec = importlib.util.spec_from_file_location('reviewed_uart', str(TRANSPORT))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def bundle():
    source = (ROOT/'launcher.py').read_bytes()
    compile(source, 'launcher.py', 'exec')
    config = (ROOT/'config.json').read_bytes()
    release_id = hashlib.sha256(source+config).hexdigest()[:16]
    release = '/home/root/aura-ui-startup-20261009/releases/'+release_id
    unit = (ROOT/'aura-avatar-ui.service.in').read_text().replace('@INSTALL_DIR@', release).encode()
    (ROOT/'aura-avatar-ui.service').write_bytes(unit)
    files = {}
    for name, data in [('launcher.py', source), ('config.json', config), ('aura-avatar-ui.service', unit)]:
        files[name] = {'sha256': hashlib.sha256(data).hexdigest(), 'bytes': len(data),
                       'base64': base64.b64encode(data).decode()}
    manifest = {'release_id': release_id, 'release': release,
                'files': {k: {f: v for f, v in d.items() if f != 'base64'} for k, d in files.items()}}
    (ROOT/'release_manifest.json').write_text(json.dumps(manifest, indent=2)+'\n')
    payload = base64.b64encode(gzip.compress(json.dumps(files, separators=(',', ':')).encode(), mtime=0)).decode()
    return manifest, payload


def wire(source):
    compile(source, '<board startup>', 'exec')
    encoded = base64.b64encode(gzip.compress(source.encode(), mtime=0)).decode()
    result = 'python3 -B -c '+shlex.quote('import base64,gzip;exec(gzip.decompress(base64.b64decode('+repr(encoded)+')))')
    wrapper = next(s for s in transport_module().UART.command.__code__.co_consts
                   if isinstance(s, str) and s.startswith('import subprocess,sys,base64,gzip,hashlib,time;'))
    outer = 'python3 -B -c '+shlex.quote(wrapper)+' '+shlex.quote(base64.b64encode(result.encode()).decode())+' AS999'
    assert len(outer.encode()) <= 3800, (len(result.encode()), len(outer.encode()))
    return result


def programs(manifest):
    common = r'''
import hashlib,json,os,shutil,signal,subprocess,time,urllib.request
from pathlib import Path
root=Path('/home/root/aura-avatar-gtk-stage/runtime-1a8677ce-20261009')
env=dict(os.environ,DISPLAY=':0',PYTHONUNBUFFERED='1')
unit=Path('/etc/systemd/system/aura-avatar-ui.service')
def run(args):
 p=subprocess.run(args,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=18)
 assert p.returncode==0,(args,p.stdout)
 return p.stdout
def api(message=None):
 address='http://127.0.0.1:8783'
 q=address+'/api/state' if message is None else urllib.request.Request(address+'/api/command',data=json.dumps(message).encode(),headers={'Content-Type':'application/json','Origin':address})
 with urllib.request.urlopen(q,timeout=12) as r:return json.load(r)
def digest(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def processes():
 result={}
 for p in Path('/proc').iterdir():
  if not p.name.isdigit():continue
  try:args=(p/'cmdline').read_bytes().decode(errors='replace').split(chr(0));stat=(p/'stat').read_text().split(') ')[1].split()
  except OSError:continue
  for name in ['Xorg','dfx-mgrd','realtime_vision.py','board_avatar_gtk.py','gstreamer_audio_worker.py']:
   if any(Path(a).name==name for a in args if a):result.setdefault(name,[]).append({'pid':int(p.name),'start_ticks':stat[19],'ppid':int(stat[1])})
 return result
def protected():
 return {s:digest(s) for s in ['/lib/systemd/system/xserver-nodm.service','/etc/default/xserver-nodm','/etc/modules-load.d/aura-touch.conf']}
'''
    common += 'manifest='+repr(manifest)+'\nrelease=Path(manifest["release"])\n'
    bodies = {
        'install': r'''
for name,record in manifest['files'].items():
 p=release/name;assert not p.is_symlink() and p.stat().st_size==record['bytes'] and digest(p)==record['sha256']
preflight=run(['python3','-B',str(release/'launcher.py'),'--config',str(release/'config.json'),'--preflight'])
backup=release/'backup';backup.mkdir(exist_ok=False)
for name in ['launch.json','stage.log','avatar_user_settings.json']:
 p=root/name
 if p.exists():shutil.copy2(str(p),str(backup/name))
before={'processes':processes(),'protected':protected(),'boot_id':Path('/proc/sys/kernel/random/boot_id').read_text().strip()}
assert not unit.exists() and not unit.is_symlink(),'Refuse to replace an existing service'
with (backup/'before.json').open('x') as f:json.dump(before,f,indent=2)
with unit.open('xb') as f:f.write((release/'aura-avatar-ui.service').read_bytes());f.flush();os.fsync(f.fileno())
run(['systemctl','daemon-reload'])
verify=run(['systemctl','show',unit.name,'-p','LoadState','-p','LoadError','-p','Type','-p','NotifyAccess','-p','KillMode','-p','Restart'])
assert {'LoadState=loaded','Type=notify','NotifyAccess=main','KillMode=mixed','Restart=on-failure'}<=set(verify.splitlines()),verify
assert digest(unit)==manifest['files'][unit.name]['sha256']
print(json.dumps({'complete':True,'backup':str(backup),'before':before,'preflight':preflight,'verify':verify}))
''',
        'enable': r'''
assert digest(unit)==manifest['files'][unit.name]['sha256']
enabled=run(['systemctl','enable',unit.name])
print(json.dumps({'complete':True,'enable':enabled,'enabled':run(['systemctl','is-enabled',unit.name]).strip()}))
''',
        'activate': r'''
assert digest(unit)==manifest['files'][unit.name]['sha256']
assert run(['systemctl','show',unit.name,'-p','MainPID','--value']).strip()=='0'
state=api();assert state['phase']=='IDLE' and not state['playing'] and not state['paused']
assert not state['ui_settings']['pending']
record=api({'type':'save_evidence'});assert record['ok'],record
info=json.loads((root/'launch.json').read_text());pid=info['pid'];p=Path('/proc')/str(pid)
source=str(root/'aura/tools/board_avatar_gtk.py').encode()
assert source in (p/'cmdline').read_bytes().split(b'\0')
assert digest(source.decode())==json.loads((release/'config.json').read_text())['gui_sha256']
before=processes();os.kill(pid,signal.SIGTERM);deadline=time.monotonic()+8
while p.exists() and time.monotonic()<deadline:
 try:
  if (p/'stat').read_text().split(') ')[1].startswith('Z '):break
 except FileNotFoundError:break
 time.sleep(.1)
assert not p.exists() or (p/'stat').read_text().split(') ')[1].startswith('Z ')
log=root/'stage.log';assert not log.is_symlink()
log.rename(release/'backup/manual-stage-final.log')
run(['systemctl','--no-block','start',unit.name])
print(json.dumps({'complete':True,'stopped_owned_ui_pid':pid,'previous_report':record,'before':before,'state_before':state,'startup_requested':True,'boot_id':info['boot_id']}))
''',
        'status': r'''
try:state=api()
except Exception as e:state={'api_error':str(e)}
info=json.loads((root/'launch.json').read_text())
status=run(['systemctl','show',unit.name,'-p','ActiveState','-p','SubState','-p','MainPID','-p','Result','-p','NRestarts','-p','ExecMainStatus','-p','UnitFileState','-p','ControlGroup'])
checks={'display':run(['xrandr','--current']),'touch':run(['xinput','list','--long','WaveShare WS170120']),'enabled':run(['systemctl','is-enabled',unit.name]).strip()}
print(json.dumps({'service':status,'state':state,'launch':info,'log':(root/'stage.log').read_text()[-3000:] if (root/'stage.log').exists() else None,'journal':run(['journalctl','-u',unit.name,'-n','16','--no-pager']),'processes':processes(),'protected':protected(),'checks':checks,'unit_sha256':digest(unit),'module_sha256':digest('/lib/modules/5.15.36-xilinx-v2022.2/extra/aura/hid-multitouch.ko'),'saved_settings':json.loads((root/'avatar_user_settings.json').read_text()),'boot_id':Path('/proc/sys/kernel/random/boot_id').read_text().strip()},ensure_ascii=False))
''',
        'restart': r'''
assert digest(unit)==manifest['files'][unit.name]['sha256']
assert run(['systemctl','is-active',unit.name]).strip()=='active'
state=api();assert state['phase']=='IDLE' and not state['playing'] and not state['paused'] and not state['ui_settings']['pending']
info=json.loads((root/'launch.json').read_text())
assert run(['systemctl','show',unit.name,'-p','MainPID','--value']).strip()==str(info['supervisor_pid'])
before={'processes':processes(),'launch':info,'state':state,'saved_settings':json.loads((root/'avatar_user_settings.json').read_text()),'protected':protected()}
run(['systemctl','--no-block','restart',unit.name])
print(json.dumps({'complete':True,'service_restart_requested':True,'before':before}))
''',
        'retry': r'''
import socket
assert digest(unit)==manifest['files'][unit.name]['sha256']
assert run(['systemctl','show',unit.name,'-p','MainPID','--value']).strip()=='0'
assert not processes().get('board_avatar_gtk.py')
network=[line.strip() for line in Path('/proc/net/tcp').read_text().splitlines() if ':224F ' in line.upper()]
with socket.socket() as p:p.bind(('127.0.0.1',8783))
run(['systemctl','reset-failed',unit.name]);run(['systemctl','--no-block','start',unit.name])
print(json.dumps({'complete':True,'port_before_retry':network,'temporary_retry_requested':True}))
''',
        'replace': r'''
assert digest(unit)=='d1e46b6c791238b74c3cd48b368d1305bc026c27e380621570a47bec555f77c6'
for name,record in manifest['files'].items():assert digest(release/name)==record['sha256']
run(['python3','-B',str(release/'launcher.py'),'--config',str(release/'config.json'),'--preflight'])
state=api();assert state['phase']=='IDLE' and not state['playing'] and not state['paused'] and not state['ui_settings']['pending']
before={'state':state,'launch':json.loads((root/'launch.json').read_text()),'processes':processes(),'protected':protected()}
backup=release/'backup';backup.mkdir(exist_ok=False)
shutil.copy2(str(unit),str(backup/unit.name))
with (backup/'before.json').open('x') as f:json.dump(before,f,indent=2)
run(['systemctl','stop',unit.name])
temporary=unit.with_suffix('.service.new')
with temporary.open('xb') as f:f.write((release/unit.name).read_bytes());f.flush();os.fsync(f.fileno())
os.replace(str(temporary),str(unit));run(['systemctl','daemon-reload']);run(['systemctl','reset-failed',unit.name]);run(['systemctl','--no-block','start',unit.name])
print(json.dumps({'complete':True,'backup':str(backup),'before':before,'replacement_requested':True}))
''',
    }
    return {name: wire(common+body) for name, body in bodies.items()}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--phase', choices=['stage', 'install', 'enable', 'activate', 'status', 'restart', 'retry', 'replace'], required=True)
    parser.add_argument('--validate', action='store_true')
    args = parser.parse_args()
    manifest, payload = bundle()
    commands = programs(manifest)
    stage = Path(manifest['release'])/'bundle.part'
    header = wire("import json,hashlib\nfrom pathlib import Path\np=Path("+repr(str(stage))+");p.parent.mkdir(parents=True,exist_ok=True)\nassert not p.is_symlink()\nd=p.read_bytes() if p.exists() else b''\nprint(json.dumps({'offset':len(d),'sha256':hashlib.sha256(d).hexdigest()}))")
    finish = wire("import json,hashlib,base64,gzip,os\nfrom pathlib import Path\np=Path("+repr(str(stage))+"\n)\ndata=p.read_bytes();assert hashlib.sha256(data).hexdigest()=="+repr(hashlib.sha256(payload.encode()).hexdigest())+"\nfiles=json.loads(gzip.decompress(base64.b64decode(data)));result={}\nassert set(files)=={'launcher.py','config.json','aura-avatar-ui.service'}\nfor name,record in files.items():\n d=base64.b64decode(record['base64']);assert len(d)==record['bytes'] and hashlib.sha256(d).hexdigest()==record['sha256']\n if name.endswith('.py'):compile(d,name,'exec')\n target=p.parent/name\n if target.exists():assert not target.is_symlink() and target.read_bytes()==d\n else:\n  with target.open('xb') as f:f.write(d);f.flush();os.fsync(f.fileno())\n result[name]={'bytes':target.stat().st_size,'sha256':hashlib.sha256(target.read_bytes()).hexdigest()}\nprint(json.dumps({'complete':True,'files':result}))")
    chunks = []
    for offset in range(0, len(payload), 1500):
        value = payload[offset:offset+1500]
        code = "import json,hashlib,os\nfrom pathlib import Path\np=Path("+repr(str(stage))+");assert not p.is_symlink()\nassert (p.stat().st_size if p.exists() else 0)=="+str(offset)+"\nwith p.open('ab') as f:f.write("+repr(value.encode())+");f.flush();os.fsync(f.fileno())\nprint(json.dumps({'offset':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}))"
        chunks.append((offset, wire(code)))
    if args.validate:
        print(json.dumps({'release_id':manifest['release_id'],'payload_characters':len(payload),'commands':{k:len(v) for k,v in commands.items()},'stage_commands':len(chunks)+2,'largest_chunk_command':max(len(v) for _,v in chunks),'board_accessed':False}));return 0
    transport=transport_module()
    evidence=ROOT/'evidence'/datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ-'+args.phase)
    evidence.mkdir(parents=True);status={'phase':args.phase,'release_id':manifest['release_id'],'complete':False,'commands':[]};uart=None
    with (evidence/'serial.raw').open('xb') as raw:
        try:
            uart=transport.UART(raw);uart.connect()
            print(json.dumps({'evidence':str(evidence),'root_shell_confirmed':True}),flush=True)
            def send(command, label):
                sequence='AS'+str(len(status['commands'])+1).zfill(3)
                rc,data,sha=uart.command(command,sequence,55)
                output=evidence/(sequence+'-'+label+'.output');output.write_bytes(data)
                status['commands'].append({'sequence':sequence,'label':label,'exit_code':rc,'bytes':len(data),'sha256':sha,'output':output.name})
                if rc:raise RuntimeError(data.decode(errors='replace')[-2400:])
                result=json.loads(data)
                (output.with_suffix('.json')).write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
                return result
            if args.phase=='stage':
                result=send(header,'offset');offset=result['offset']
                assert offset<=len(payload) and hashlib.sha256(payload[:offset].encode()).hexdigest()==result['sha256']
                assert offset==len(payload) or offset%1500==0
                for start,command in chunks:
                    if start<offset:continue
                    result=send(command,'chunk')
                    assert result['offset']==min(start+1500,len(payload))
                    assert result['sha256']==hashlib.sha256(payload[:result['offset']].encode()).hexdigest()
                result=send(finish,'finish')
                assert result['files']==manifest['files']
            else:result=send(commands[args.phase],args.phase)
            (evidence/'result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
            print(json.dumps({k:v for k,v in result.items() if k not in ['log','journal']},ensure_ascii=False)[:3000],flush=True)
            status['complete']=True
        except Exception as exc:status['error']=str(exc)
        finally:
            if uart is not None:status['console_echo_restored']=uart.close()
    (evidence/'status.json').write_text(json.dumps(status,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(status,ensure_ascii=False),flush=True)
    return 0 if status['complete'] and status.get('console_echo_restored') else 1


if __name__=='__main__':raise SystemExit(main())
