#!/usr/bin/env python3
"""Deploy the reviewed 18KB native probe into one new board directory.

Only this immutable ZIP is accepted. No firmware/configuration changes, device
playback, camera access, external process control, or overwrite of existing files.
"""
import argparse
import base64
import datetime
import gzip
import hashlib
import importlib.util
import json
from pathlib import Path
import shlex
import sys

ROOT = Path(__file__).resolve().parent
ARCHIVE = Path('/home/ghmd/Win共享文件/共享文件夹/aura/artifacts/releases/aura-board-avatar-gtk-native-probe-20261009T111150Z-bf9367.zip')
EXPECTED = 'c9a53bcb97d3acda2243036bfb7e911a2363c3bb02ca41d3ad7d1f57076c71de'
DESTINATION = '/home/root/aura-avatar-gtk-stage/native-probe-c9a53bcb97d3acda'
TRANSPORT = Path('/home/ghmd/kv260-dfx-state-boardtest-20261004/scripts/uart_phase.py')


def python_command(source):
    blob = base64.b64encode(gzip.compress(source.encode(),mtime=0)).decode()
    code = 'import base64,gzip;exec(gzip.decompress(base64.b64decode('+repr(blob)+')))'
    return 'python3 -B -c '+shlex.quote(code)


def utc():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--validate',action='store_true')
    args=parser.parse_args()
    payload=ARCHIVE.read_bytes()
    if len(payload)>1024*1024 or hashlib.sha256(payload).hexdigest()!=EXPECTED:
        raise RuntimeError('Reviewed native-probe archive changed')
    if args.validate:
        print(json.dumps({'archive_sha256':EXPECTED,'bytes':len(payload),'new_board_directory':DESTINATION,
                          'audio_playback':False,'board_accessed':False}))
        return 0
    spec=importlib.util.spec_from_file_location('reviewed_uart',str(TRANSPORT))
    transport=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(transport)
    out=ROOT/'evidence'/datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ-native-probe')
    out.mkdir(parents=True)
    status={'started_utc':utc(),'complete':False,'archive':str(ARCHIVE),'archive_sha256':EXPECTED,
            'destination':DESTINATION,'results':[],'audio_playback':False,'firmware_changed':False}
    uart=None
    def run(name,command):
        index=len(status['results'])
        rc,data,sha=uart.command(command,'GP%03d'%index,40)
        (out/(name+'.output')).write_bytes(data)
        result={'id':name,'exit_code':rc,'bytes':len(data),'output_sha256':sha,'command':command}
        status['results'].append(result)
        (out/'status.json').write_text(json.dumps(status,indent=2)+'\n')
        if rc:
            raise RuntimeError('Board command failed: '+name)
        if not name.startswith('chunk-'):
            print(json.dumps({k:v for k,v in result.items() if k!='command'}),flush=True)
        return data
    with (out/'serial.raw').open('xb') as raw:
        try:
            uart=transport.UART(raw)
            uart.connect()
            status['root_shell_confirmed']=True
            run('create-directory',python_command('from pathlib import Path;Path('+repr(DESTINATION)+').mkdir(parents=True,exist_ok=False)'))
            for index,start in enumerate(range(0,len(payload),768)):
                block=payload[start:start+768]
                source="import base64,hashlib;from pathlib import Path\np=Path("+repr(DESTINATION+'/bundle.zip')+")\nb=base64.b64decode("+repr(base64.b64encode(block).decode())+")\nassert hashlib.sha256(b).hexdigest()=="+repr(hashlib.sha256(block).hexdigest())+"\nassert (p.stat().st_size if p.exists() else 0)=="+str(start)+"\nwith p.open("+repr('xb' if start==0 else 'ab')+") as f:f.write(b)\nprint(p.stat().st_size)\n"
                result=run('chunk-%03d'%index,python_command(source))
                if int(result)!=start+len(block):
                    raise RuntimeError('Transfer offset mismatch')
            source='''import hashlib,json,zipfile
from pathlib import Path
root=Path(DESTINATION)
archive=root/'bundle.zip'
assert hashlib.sha256(archive.read_bytes()).hexdigest()==EXPECTED
with zipfile.ZipFile(archive) as z:
 manifest=json.loads(z.read('runtime_manifest.json'))
 assert manifest['profile']=='native-probe'
 records=manifest['files']
 assert len(z.namelist())==len(records)+1
 assert set(z.namelist())=={r['path'] for r in records}|{'runtime_manifest.json'}
 for row in records:
  relative=Path(row['path'])
  assert not relative.is_absolute() and '..' not in relative.parts
  data=z.read(row['path'])
  assert len(data)==row['bytes'] and hashlib.sha256(data).hexdigest()==row['sha256']
  p=root/relative
  p.parent.mkdir(parents=True,exist_ok=True)
  with p.open('xb') as f:f.write(data)
 with (root/'runtime_manifest.json').open('x') as f:json.dump(manifest,f,indent=2)
 print(json.dumps({'verified_payload_files':len(records),'archive_sha256':EXPECTED}))
'''.replace('Path(DESTINATION)','Path('+repr(DESTINATION)+')').replace('==EXPECTED','=='+repr(EXPECTED)).replace("'archive_sha256':EXPECTED","'archive_sha256':"+repr(EXPECTED))
            run('unpack-verified',python_command(source))
            aura=DESTINATION+'/aura'
            run('gstreamer-libraries','python3 -B '+shlex.quote(aura+'/tools/gstreamer_audio_worker.py')+' --probe')
            run('native-clock','python3 -B '+shlex.quote(aura+'/tools/check_gstreamer_clock.py'))
            run('lifecycle-tests','cd '+shlex.quote(aura)+' && python3 -B -m unittest discover -s tests/framework -p test_gstreamer_audio.py -v')
            source="import json,os,sys;sys.path.insert(0,"+repr(aura)+");os.environ['DISPLAY']=':0'\nfrom tools.board_avatar_gtk import load_gtk\nfrom tools.pillow_compat import AFFINE,BICUBIC,LANCZOS\nfrom PIL import Image\ngtk,gdk,pixbuf,glib=load_gtk();init=gtk.init_check([])\nim=Image.new('RGBA',(2,2));result=im.transform(im.size,AFFINE,(1,0,0,0,1,0),BICUBIC)\nassert result.tobytes()==im.tobytes()\nassert (init[0] if isinstance(init,tuple) else init)\nprint(json.dumps({'gtk_display_connection':True,'pillow_legacy_constants':True,'window_created':False,'audio_playback':False}))\n"
            run('gtk-pillow',python_command(source))
            status['complete']=True
        except Exception as exc:
            status['error']=type(exc).__name__+': '+str(exc)
            print(json.dumps({'error':status['error']}),flush=True)
        finally:
            if uart is not None:
                try:status['console_echo_restored']=uart.close()
                except Exception as exc:status['console_close_error']=str(exc)
    status['finished_utc']=utc()
    (out/'status.json').write_text(json.dumps(status,indent=2)+'\n')
    print(json.dumps({'complete':status['complete'],'evidence':str(out),'console_echo_restored':status.get('console_echo_restored')}),flush=True)
    return 0 if status['complete'] and status.get('console_echo_restored') else 1


if __name__=='__main__':
    sys.exit(main())
