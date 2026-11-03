#!/usr/bin/env python3
"""Deploy a hashed, immutable CPU preview release over the known UART."""
import base64
import datetime
import gzip
import hashlib
import importlib.util
import json
from pathlib import Path
import shlex

ROOT = Path(__file__).resolve().parent
BOARD = '/home/root/aura-realtime-vision-20261007'
FILES = ['vision_core.py','x11_window.py','realtime_vision.py','test_vision_core.py','board_launch.py',
         'motion_service.py','test_motion_service.py','motion_replay.py']
sources = {name:(ROOT/name).read_text() for name in FILES}
for name, source in sources.items():
    compile(source,name,'exec')
hashes = {name:hashlib.sha256(source.encode()).hexdigest() for name, source in sources.items()}
bundle = gzip.compress(json.dumps(sources,sort_keys=True).encode(),mtime=0)
digest = hashlib.sha256(bundle).hexdigest()
stamp = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')
out = ROOT/'evidence'/stamp
out.mkdir(parents=True)
(out/'source-bundle.json.gz').write_bytes(bundle)
(out/'source-hashes.json').write_text(json.dumps(hashes,indent=2))
spec = importlib.util.spec_from_file_location('aura_uart','/home/ghmd/kv260-dfx-state-boardtest-20261004/scripts/uart_phase.py')
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
guard = "import os;from pathlib import Path;assert os.uname().machine=='aarch64';assert Path('/sys/block/mmcblk1/device/cid').read_text().strip()=='0353445345333247805558c00401a100';\n"
state = {'passed':False,'evidence':str(out),'bundle_sha256':digest,'files':hashes}
with (out/'uart.raw').open('wb') as raw:
    u = mod.UART(raw)
    try:
        u.connect()
        def execute(code,marker,timeout=40):
            (out/(marker+'.py')).write_text(guard+code)
            packed = base64.b64encode(gzip.compress((guard+code).encode(),mtime=0)).decode()
            remote = 'import base64,gzip;exec(gzip.decompress(base64.b64decode('+repr(packed)+')))'
            rc, data, sha = u.command('python3 -B -c '+shlex.quote(remote),marker,timeout)
            (out/(marker+'.txt')).write_bytes(data)
            if rc:
                raise RuntimeError(marker+': '+data.decode(errors='replace')[-3000:])
            return data
        upload = BOARD+'/bundle-'+digest+'.upload'
        release = BOARD+'/releases/'+digest[:16]
        execute('p=Path('+repr(upload)+');p.parent.mkdir(parents=True,exist_ok=True);assert not p.exists();p.write_bytes(b"")','PREPARE')
        for start in range(0,len(bundle),768):
            chunk = base64.b64encode(bundle[start:start+768]).decode()
            execute('import base64;p=Path('+repr(upload)+');f=p.open("ab");f.write(base64.b64decode('+repr(chunk)+'));f.close()','CHUNK'+str(start//768))
            if start//768%5==0:
                print('Uploaded %d/%d bytes' % (min(start+768,len(bundle)),len(bundle)),flush=True)
        unpack = ('import hashlib,gzip,json\np=Path('+repr(upload)+')\n'
                  'assert hashlib.sha256(p.read_bytes()).hexdigest()=='+repr(digest)+'\n'
                  'sources=json.loads(gzip.decompress(p.read_bytes()))\n'
                  'hashes='+repr(hashes)+'\n'
                  'assert set(sources)==set(hashes)\n'
                  'release=Path('+repr(release)+')\n'
                  'release.mkdir(parents=True,exist_ok=False)\n'
                  'for name,source in sources.items():\n'
                  ' assert hashlib.sha256(source.encode()).hexdigest()==hashes[name]\n'
                  ' (release/name).write_text(source)\n'
                  'Path('+repr(BOARD+'/staged.json')+').write_text(json.dumps({"release":str(release),"hashes":hashes}))\n'
                  'print(json.dumps({"release":str(release),"hashes":hashes}))\n')
        execute(unpack,'UNPACK')
        preflight = ('import subprocess,json\nrelease='+repr(release)+'\n'
                     'for command in [["python3","-m","unittest","-v","test_vision_core.py"],["python3","realtime_vision.py","--preflight"]]:\n'
                     ' p=subprocess.run(command,cwd=release,capture_output=True,text=True,timeout=25)\n'
                     ' print(p.stdout+p.stderr)\n'
                     ' assert p.returncode==0\n'
                     'import gi\ngi.require_version("Gst","1.0")\ngi.require_version("GstVideo","1.0")\n'
                     'from gi.repository import Gst,GstVideo\nGst.init(None)\n'
                     'info=GstVideo.VideoInfo()\nassert info.from_caps(Gst.Caps.from_string("video/x-raw,format=BGR,width=640,height=480,framerate=30/1"))\n'
                     'assert (info.width,info.height,info.stride[0])==(640,480,1920)\n'
                     'for name in ["v4l2src","appsink","appsrc","videoconvert","ximagesink"]:\n assert Gst.ElementFactory.find(name)\n'
                     'assert Gst.ElementFactory.make("appsrc").find_property("current-level-bytes")\n'
                     'print("GSTREAMER_PREFLIGHT_PASS")\n')
        execute(preflight,'PREFLIGHT',60)
        launch = 'exec(compile(Path('+repr(release+'/board_launch.py')+').read_text(),"board_launch.py","exec"))'
        result = json.loads(execute(launch,'LAUNCH',55))
        assert result['passed']
        state.update(passed=True,result=result)
    except Exception as exc:
        state['error'] = str(exc)
        raise
    finally:
        state['console_echo_restored'] = u.close()
        (out/'result.json').write_text(json.dumps(state,indent=2))
        (ROOT/'CURRENT_DEPLOY.json').write_text(json.dumps(state,indent=2))
        print(json.dumps(state,indent=2),flush=True)
