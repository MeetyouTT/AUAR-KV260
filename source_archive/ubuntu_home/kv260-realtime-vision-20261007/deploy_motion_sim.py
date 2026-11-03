#!/usr/bin/env python3
"""Stage immutable simulation software, run board tests, then owned upgrade."""
import base64
import datetime
import gzip
import hashlib
import importlib.util
import json
from pathlib import Path
import shlex

ROOT = Path(__file__).resolve().parent
ADAPT = ROOT.parent/'kv260-adaptation-check-20261006'
BOARD = '/home/root/aura-realtime-vision-20261007'
FILES = ['vision_core.py','x11_window.py','realtime_vision.py','test_vision_core.py',
         'motion_service.py','test_motion_service.py','motion_replay.py','board_motion_launch.py']
base_pointer = json.loads((ADAPT/'CURRENT_MOTION_STAGE_INVENTORY.json').read_text())
assert base_pointer['rc']==0 and base_pointer['console_echo_restored']
base = json.loads((Path(base_pointer['evidence'])/'result.txt').read_text())
assert base['same_boot'] and base['owned'] and base['owners']==[base['pid']]
assert not base['after']['error'] and not base['after']['stopped']
assert all(base['after'][k]>base['before'][k] for k in ['capture_frames','detected_frames','display_frames','rendered_frames'])
sources = {name:(ROOT/name).read_text() for name in FILES}
for name, source in sources.items():
    compile(source,name,'exec')
hashes = {name:hashlib.sha256(source.encode()).hexdigest() for name, source in sources.items()}
bundle = gzip.compress(json.dumps(sources,sort_keys=True).encode(),mtime=0)
digest = hashlib.sha256(bundle).hexdigest()
stamp = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')
out = ROOT/'evidence'/('motion-deploy-'+stamp)
out.mkdir(parents=True)
(out/'source-bundle.json.gz').write_bytes(bundle)
(out/'source-hashes.json').write_text(json.dumps(hashes,indent=2))
(out/'base-inventory.json').write_text(json.dumps(base,indent=2))
spec = importlib.util.spec_from_file_location('aura_uart','/home/ghmd/kv260-dfx-state-boardtest-20261004/scripts/uart_phase.py')
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
guard = ("import os;from pathlib import Path;assert os.uname().machine=='aarch64';"
         "assert Path('/sys/block/mmcblk1/device/cid').read_text().strip()=='0353445345333247805558c00401a100';"
         "assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()=="+repr(base['boot_id'])+";\n")
state = {'passed':False,'evidence':str(out),'bundle_sha256':digest,'files':hashes,
         'motion_command_emitted':False,'fpga_modified':False}
with (out/'uart.raw').open('wb') as raw:
    uart = mod.UART(raw)
    try:
        uart.connect()
        def execute(code, marker, timeout=40):
            (out/(marker+'.py')).write_text(guard+code)
            packed = base64.b64encode(gzip.compress((guard+code).encode(),mtime=0)).decode()
            remote = 'import base64,gzip;exec(gzip.decompress(base64.b64decode('+repr(packed)+')))'
            rc, data, sha = uart.command('python3 -B -c '+shlex.quote(remote),marker,timeout)
            (out/(marker+'.txt')).write_bytes(data)
            (out/(marker+'.integrity.json')).write_text(json.dumps({'rc':rc,'output_sha256':sha}))
            if rc:
                raise RuntimeError(marker+': '+data.decode(errors='replace')[-2500:])
            return data
        upload = BOARD+'/motion-bundle-'+digest+'.upload'
        release = BOARD+'/releases/'+digest[:16]
        execute('p=Path('+repr(upload)+');p.parent.mkdir(parents=True,exist_ok=True);assert not p.exists();p.write_bytes(b"")','PREPARE')
        for start in range(0,len(bundle),768):
            chunk = base64.b64encode(bundle[start:start+768]).decode()
            execute('import base64;p=Path('+repr(upload)+');f=p.open("ab");f.write(base64.b64decode('+repr(chunk)+'));f.close()','CHUNK'+str(start//768))
            if start//768%5==0:
                print('Uploaded %d/%d bytes' % (min(start+768,len(bundle)),len(bundle)),flush=True)
        reduced = {k:base[k] for k in ['boot_id','pid','current_release','hashes']}
        unpack = ('import hashlib,gzip,json\np=Path('+repr(upload)+')\n'
                  'assert hashlib.sha256(p.read_bytes()).hexdigest()=='+repr(digest)+'\n'
                  'sources=json.loads(gzip.decompress(p.read_bytes()))\nhashes='+repr(hashes)+'\n'
                  'assert set(sources)==set(hashes)\nrelease=Path('+repr(release)+')\n'
                  'release.mkdir(parents=True,exist_ok=False)\n'
                  'for name,source in sources.items():\n'
                  ' assert hashlib.sha256(source.encode()).hexdigest()==hashes[name]\n'
                  ' (release/name).write_text(source)\n'
                  'stage={"release":str(release),"hashes":hashes,"base":'+repr(reduced)+'}\n'
                  'Path('+repr(BOARD+'/motion-staged.json')+').write_text(json.dumps(stage))\n'
                  'print(json.dumps(stage))\n')
        execute(unpack,'UNPACK')
        preflight = ('import subprocess,json\nrelease='+repr(release)+'\n'
                     'for command in [["python3","-m","unittest","-v","test_motion_service.py","test_vision_core.py"],'
                     '["python3","motion_replay.py"],["python3","realtime_vision.py","--preflight"]]:\n'
                     ' p=subprocess.run(command,cwd=release,capture_output=True,text=True,timeout=35)\n'
                     ' print(p.stdout+p.stderr)\n assert p.returncode==0\n')
        execute(preflight,'PREFLIGHT',60)
        launch = 'exec(compile(Path('+repr(release+'/board_motion_launch.py')+').read_text(),"board_motion_launch.py","exec"))'
        result = json.loads(execute(launch,'LAUNCH',60))
        assert result['passed'] and result['scope']=='SIMULATED'
        state.update(passed=True,result=result)
    except Exception as exc:
        state['error'] = str(exc)
        raise
    finally:
        state['console_echo_restored'] = uart.close()
        (out/'result.json').write_text(json.dumps(state,indent=2))
        (ROOT/'CURRENT_MOTION_DEPLOY.json').write_text(json.dumps(state,indent=2))
        print(json.dumps({k:v for k,v in state.items() if k!='result'},indent=2),flush=True)
