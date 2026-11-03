#!/usr/bin/env python3
"""Reviewed single-UART staging and UI-only deployment/test orchestration."""
import argparse
import base64
import datetime
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import re
import shlex
import zipfile

WORK = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location('startup_wire','/home/ghmd/aura-board-ui-autostart-20261009/manage_startup.py')
WIRE = importlib.util.module_from_spec(SPEC);SPEC.loader.exec_module(WIRE)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--phase',choices=('stage','inspect','apply','status','page','keypad','fixture','rollback','camera-inspect'),required=True)
    parser.add_argument('--page',choices=('main','demo','devices','connection','settings'),default='main')
    parser.add_argument('--validate',action='store_true')
    parser.add_argument('--base-update',help='Reuse only unchanged, hash-verified files from this staged update')
    args = parser.parse_args()
    meta = json.loads((WORK/'package_validation.json').read_text())
    manifest = json.loads((WORK/'manifest.json').read_text())
    archive = Path(meta['archive']).read_bytes()
    assert len(archive) == meta['bytes'] and hashlib.sha256(archive).hexdigest() == meta['sha256']
    stage = '/home/root/aura-avatar-gtk-stage/runtime-1a8677ce-20261009/ui-design-update-'+meta['update_id']
    base_stage = ''
    if args.base_update:
        assert args.phase == 'stage' and re.fullmatch('[0-9a-f]{16}',args.base_update)
        base_stage = stage.rsplit('-',1)[0]+'-'+args.base_update
        with zipfile.ZipFile(WORK/('aura-board-ui-update-'+args.base_update+'.zip')) as old:
            old_manifest = json.loads(old.read('manifest.json'))
        assert old_manifest['update_id'] == args.base_update
        changed = {name for name,row in manifest['files'].items() if old_manifest['files'].get(name) != row}
        buffer = io.BytesIO()
        with zipfile.ZipFile(io.BytesIO(archive)) as full,zipfile.ZipFile(buffer,'w',compression=zipfile.ZIP_DEFLATED) as delta:
            for name in sorted(changed|{'manifest.json'}):
                info = zipfile.ZipInfo(name,date_time=(2026,10,10,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED
                delta.writestr(info,full.read(name))
        archive = buffer.getvalue()
        (WORK/('delta-'+meta['update_id']+'.zip')).write_bytes(archive)
    transfer_sha256 = hashlib.sha256(archive).hexdigest()
    payload = base64.b64encode(archive).decode()
    commands = []
    if args.phase == 'camera-inspect':
        commands.append(('camera-inspect',WIRE.wire((WORK/'board_camera_inspect.py').read_text()),60))
    elif args.phase == 'stage':
        commands.append(('prepare',WIRE.wire('from pathlib import Path;Path('+repr(stage)+').mkdir(exist_ok=True)'),20))
        for index,start in enumerate(range(0,len(payload),1500)):
            data = payload[start:start+1500]
            program = 'from pathlib import Path;import hashlib\np=Path('+repr(stage+'/update.zip.b64.part')+')\ns='+repr(data)+'\n'
            program += 'n=p.stat().st_size if p.exists() else 0\nassert n>='+str(start)+'\n'
            program += 'if n=='+str(start)+':\n with p.open("ab") as f:f.write(s.encode())\n'
            program += 'assert hashlib.sha256(p.read_bytes()[:'+str(start+len(data))+']).hexdigest()=='+repr(hashlib.sha256(payload[:start+len(data)].encode()).hexdigest())+'\nprint(p.stat().st_size)'
            commands.append(('chunk-%03d'%index,WIRE.wire(program),20))
        program = '''
import base64,hashlib,json,zipfile,io
from pathlib import Path,PurePosixPath
root=Path(STAGE);data=base64.b64decode((root/'update.zip.b64.part').read_bytes(),validate=True)
assert len(data)==SIZE and hashlib.sha256(data).hexdigest()==SHA
with zipfile.ZipFile(io.BytesIO(data)) as archive:
 assert archive.testzip() is None
 manifest=json.loads(archive.read('manifest.json'))
 assert 'manifest.json' in archive.namelist() and set(archive.namelist())<=set(manifest['files'])|{'manifest.json'}
 if not BASE:assert set(archive.namelist())==set(manifest['files'])|{'manifest.json'}
 for name in list(manifest['files'])+['manifest.json']:
  rel=PurePosixPath(name);assert not rel.is_absolute() and '..' not in rel.parts
  blob=archive.read(name) if name in archive.namelist() else (Path(BASE)/'payload'/name).read_bytes()
  if name!='manifest.json':
   row=manifest['files'][name];assert len(blob)==row['bytes'] and hashlib.sha256(blob).hexdigest()==row['sha256']
  if name.endswith('.py'):compile(blob,name,'exec')
  p=root/'payload'/name;p.parent.mkdir(parents=True,exist_ok=True)
  if p.exists():assert p.read_bytes()==blob
  else:
   with p.open('xb') as stream:stream.write(blob)
print(json.dumps({'stage_verified':True,'transfer_sha256':SHA,'reused_base':BASE,'files':manifest['files']}))
'''
        program = 'STAGE='+repr(stage)+'\nBASE='+repr(base_stage)+'\nSIZE='+str(len(archive))+'\nSHA='+repr(transfer_sha256)+'\n'+program
        commands.append(('unpack-verify',WIRE.wire(program),30))
    else:
        name = 'board_probe.py' if args.phase in ('page','keypad','fixture') else 'board_apply.py'
        path = stage+'/payload/'+name
        command = 'python3 -B '+shlex.quote(path)+' --phase '+args.phase
        if args.phase == 'page':command += ' --page '+args.page
        check = 'import hashlib,subprocess\np='+repr(path)+'\nassert hashlib.sha256(open(p,"rb").read()).hexdigest()=='+repr(manifest['files'][name]['sha256'])+'\n'
        check += 'raise SystemExit(subprocess.call('+repr(command)+',shell=True))'
        commands.append((args.phase+'-'+args.page if args.phase == 'page' else args.phase,WIRE.wire(check),120 if args.phase == 'apply' else 60))
    if args.validate:
        print(json.dumps({'phase':args.phase,'commands':len(commands),'stage':stage,'board_accessed':False}));return 0
    folder = WORK/'evidence'/datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ-'+args.phase+('-'+args.page if args.phase == 'page' else ''))
    folder.mkdir(parents=True)
    result = {'phase':args.phase,'update_id':meta['update_id'],'stage':stage,'complete':False,'commands':[]}
    uart = None
    raw = (folder/'serial.raw').open('xb')
    try:
        uart = WIRE.transport_module().UART(raw);uart.connect()
        print(json.dumps({'evidence':str(folder),'root_shell_confirmed':True}),flush=True)
        for index,(label,command,timeout) in enumerate(commands):
            rc,body,digest = uart.command(command,'UI%03d'%index,timeout)
            output = label+'.output';(folder/output).write_bytes(body)
            row = {'sequence':index,'label':label,'exit_code':rc,'bytes':len(body),'sha256':digest,'output':output}
            result['commands'].append(row)
            (folder/'result.json').write_text(json.dumps(result,indent=2)+'\n')
            if rc:raise RuntimeError(label+': '+body.decode(errors='replace')[:3500])
            if not label.startswith('chunk-'):
                try:
                    value = json.loads(body)
                    shot = value.get('screenshot')
                    if shot:
                        image = base64.b64decode(shot['jpeg_base64'],validate=True)
                        assert len(image) == shot['bytes'] and hashlib.sha256(image).hexdigest() == shot['sha256']
                        (folder/'screen.jpg').write_bytes(image)
                        value['screenshot'] = {k:v for k,v in shot.items() if k != 'jpeg_base64'}
                    (folder/(label+'.json')).write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n')
                    print(json.dumps({'step':label,'result':value},ensure_ascii=False)[:4000],flush=True)
                except json.JSONDecodeError:
                    print(json.dumps({'step':label,'output':body.decode(errors='replace')[:1000]}),flush=True)
        result['complete'] = True
    except Exception as exc:
        result['error'] = type(exc).__name__+': '+str(exc);print(json.dumps({'error':result['error']}),flush=True)
    finally:
        if uart:
            try:result['console_echo_restored'] = uart.close()
            except Exception as exc:result['console_error'] = str(exc)
        raw.close()
        (folder/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({'complete':result['complete'],'console_echo_restored':result.get('console_echo_restored'),'evidence':str(folder)}),flush=True)
    return 0 if result['complete'] and result.get('console_echo_restored') else 1


if __name__ == '__main__':raise SystemExit(main())
