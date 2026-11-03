#!/usr/bin/env python3
"""Apply the pinned five-file settings update to the owned avatar installation."""
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

ROOT=Path(__file__).resolve().parent
ARCHIVE=ROOT/'touch_settings_update.zip'
EXPECTED='ddd4944081890e22e76d1bd105106059ae3cea09636fe6f97c2093868a09b661'
DEST='/home/root/aura-avatar-gtk-stage/runtime-1a8677ce-20261009'
UPDATE=DEST+'/touch-update-ddd4944081890e22'
TRANSPORT=Path('/home/ghmd/kv260-dfx-state-boardtest-20261004/scripts/uart_phase.py')


def command_for(source):
    ast.parse(source)
    blob=base64.b64encode(gzip.compress(source.encode(),mtime=0)).decode()
    code='import base64,gzip;exec(gzip.decompress(base64.b64decode('+repr(blob)+')))'
    command='python3 -B -c '+shlex.quote(code)
    if len(base64.b64encode(command.encode()))+900>3800:
        raise ValueError('UART command too long')
    return command


APPLY='''
import hashlib,json,os,signal,time,urllib.request,zipfile
from pathlib import Path,PurePosixPath
root=Path(DEST);update=Path(UPDATE)
archive=update/'update.zip'
assert hashlib.sha256(archive.read_bytes()).hexdigest()==EXPECTED
with zipfile.ZipFile(archive) as z:
 manifest=json.loads(z.read('update_manifest.json'));rows=manifest['files']
 assert manifest['kind']=='GTK_TOUCH_SETTINGS_UPDATE' and len(rows)==5
 assert set(z.namelist())=={r['path'] for r in rows}|{'update_manifest.json'}
 for row in rows:
  rel=PurePosixPath(row['path']);assert not rel.is_absolute() and '..' not in rel.parts and rel.parts[0]=='aura'
  data=z.read(row['path']);assert len(data)==row['bytes'] and hashlib.sha256(data).hexdigest()==row['sha256']
  p=root/row['path']
  if row['before_sha256']:assert hashlib.sha256(p.read_bytes()).hexdigest()==row['before_sha256'],row['path']
  else:assert not p.exists(),row['path']
  target=update/'payload'/row['path'];target.parent.mkdir(parents=True,exist_ok=True)
  with target.open('xb') as f:f.write(data)
  if p.exists():
   backup=update/'backup'/row['path'];backup.parent.mkdir(parents=True,exist_ok=True)
   with backup.open('xb') as f:f.write(p.read_bytes())
info=json.loads((root/'launch.json').read_text());pid=info['pid']
assert info['boot_id']==Path('/proc/sys/kernel/random/boot_id').read_text().strip()
assert str(root/'aura/tools/board_avatar_gtk.py').encode() in Path('/proc/'+str(pid)+'/cmdline').read_bytes().split(bytes([0]))
for data in [{'type':'event','event':'cancel'},{'type':'save_evidence'}]:
 req=urllib.request.Request('http://127.0.0.1:8783/api/command',data=json.dumps(data).encode(),headers={'Content-Type':'application/json','Origin':'http://127.0.0.1:8783'})
 with urllib.request.urlopen(req,timeout=8) as r:assert json.load(r)['ok']
os.kill(pid,signal.SIGTERM);deadline=time.monotonic()+5
while Path('/proc/'+str(pid)+'/stat').exists() and time.monotonic()<deadline:
 if Path('/proc/'+str(pid)+'/stat').read_text().split(') ')[1].startswith('Z '):break
 time.sleep(.1)
assert not Path('/proc/'+str(pid)+'/stat').exists() or Path('/proc/'+str(pid)+'/stat').read_text().split(') ')[1].startswith('Z ')
for row in rows:
 p=root/row['path'];tmp=p.with_name(p.name+'.touch-new')
 with tmp.open('xb') as f:f.write((update/'payload'/row['path']).read_bytes());f.flush();os.fsync(f.fileno())
 os.replace(str(tmp),str(p));assert hashlib.sha256(p.read_bytes()).hexdigest()==row['sha256']
for name in ['launch.json','stage.log','run-evidence']:(root/name).rename(update/'backup'/name)
result={'applied_files':rows,'stopped_only_owned_pid':pid,'update_sha256':EXPECTED,'backup':str(update/'backup')}
with (update/'APPLIED.json').open('x') as f:json.dump(result,f,indent=2)
print(json.dumps(result))
'''
APPLY='DEST='+repr(DEST)+'\nUPDATE='+repr(UPDATE)+'\nEXPECTED='+repr(EXPECTED)+'\n'+APPLY

START='''
import json,os,subprocess
from pathlib import Path
root=Path(DEST)
assert not (root/'launch.json').exists() and not (root/'run-evidence').exists()
args=['python3','-B',str(root/'aura/tools/board_avatar_gtk.py'),'--evidence-root',str(root/'run-evidence')]
env=dict(os.environ,DISPLAY=':0',PYTHONUNBUFFERED='1')
with (root/'stage.log').open('xb') as log:
 p=subprocess.Popen(args,cwd=str(root/'aura'),env=env,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
info={'pid':p.pid,'args':args,'evidence':str(root/'run-evidence'),'boot_id':Path('/proc/sys/kernel/random/boot_id').read_text().strip()}
with (root/'launch.json').open('x') as f:json.dump(info,f,indent=2)
print(json.dumps(info))
'''
START='DEST='+repr(DEST)+'\n'+START


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--validate',action='store_true')
    args=parser.parse_args()
    payload=ARCHIVE.read_bytes()
    assert len(payload)==16256 and hashlib.sha256(payload).hexdigest()==EXPECTED
    command_for(APPLY);command_for(START)
    if args.validate:
        print(json.dumps({'archive_sha256':EXPECTED,'bytes':len(payload),'new_update_directory':UPDATE,'board_accessed':False}))
        return 0
    spec=importlib.util.spec_from_file_location('reviewed_uart',str(TRANSPORT))
    transport=importlib.util.module_from_spec(spec);spec.loader.exec_module(transport)
    out=ROOT/'evidence'/datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ-deploy')
    out.mkdir(parents=True)
    status={'complete':False,'archive_sha256':EXPECTED,'update_directory':UPDATE,'commands':[]}
    uart=None
    def run(name,command,timeout=40):
        rc,data,sha=uart.command(command,'TS%03d'%len(status['commands']),timeout)
        (out/(name+'.output')).write_bytes(data)
        status['commands'].append({'name':name,'exit_code':rc,'bytes':len(data),'sha256':sha,'command':command})
        (out/'status.json').write_text(json.dumps(status,indent=2)+'\n')
        if rc:raise RuntimeError(name+': '+data.decode(errors='replace')[:4000])
        if not name.startswith('chunk-'):print(json.dumps({'step':name,'output':data.decode(errors='replace')[:6000]}),flush=True)
        return data
    with (out/'serial.raw').open('xb') as raw:
        try:
            uart=transport.UART(raw);uart.connect()
            print(json.dumps({'root_shell_confirmed':True,'evidence':str(out)}),flush=True)
            run('create-update',command_for('from pathlib import Path;Path('+repr(UPDATE)+').mkdir(exist_ok=False)'))
            for index,start in enumerate(range(0,len(payload),768)):
                block=payload[start:start+768]
                source="import base64,hashlib;from pathlib import Path\np=Path("+repr(UPDATE+'/update.zip')+")\nb=base64.b64decode("+repr(base64.b64encode(block).decode())+")\nassert hashlib.sha256(b).hexdigest()=="+repr(hashlib.sha256(block).hexdigest())+"\nassert (p.stat().st_size if p.exists() else 0)=="+str(start)+"\nwith p.open("+repr('xb' if start==0 else 'ab')+") as f:f.write(b)\nprint(p.stat().st_size)\n"
                result=run('chunk-%03d'%index,command_for(source))
                assert int(result)==start+len(block)
            run('apply-backed-up-update',command_for(APPLY),60)
            aura=DEST+'/aura'
            run('native-settings-tests','cd '+shlex.quote(aura)+' && python3 -B -m unittest discover -s tests/framework -p test_board_ui_settings.py -v')
            run('resource-check','cd '+shlex.quote(aura)+' && DISPLAY=:0 python3 -B tools/board_avatar_gtk.py --check',60)
            run('start-settings-ui',command_for(START))
            status['complete']=True
        except Exception as exc:
            status['error']=type(exc).__name__+': '+str(exc);print(json.dumps({'error':status['error']}),flush=True)
        finally:
            if uart is not None:
                try:status['console_echo_restored']=uart.close()
                except Exception as exc:status['console_error']=str(exc)
    (out/'status.json').write_text(json.dumps(status,indent=2)+'\n')
    print(json.dumps({'complete':status['complete'],'console_echo_restored':status.get('console_echo_restored'),'evidence':str(out)}),flush=True)
    return 0 if status['complete'] and status.get('console_echo_restored') else 1


if __name__=='__main__':sys.exit(main())
