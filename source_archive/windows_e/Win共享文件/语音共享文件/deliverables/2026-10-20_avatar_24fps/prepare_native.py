import base64,json,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent;sys.path.insert(0,str(HERE.parent/'2026-10-18_board_dialogue'))
from board_ssh import ssh
files={n:base64.b64encode((HERE/n).read_bytes()).decode() for n in ('native_pixels.cpp','native_pixels.py')}
remote=r'''
import base64,json,subprocess
from pathlib import Path
stage=Path('/home/root/aura-render24-prototype-20261020');stage.mkdir(exist_ok=True)
for n,raw in FILES.items():(stage/n).write_bytes(base64.b64decode(raw))
flags=subprocess.check_output(['pkg-config','--cflags','--libs','gstreamer-app-1.0','gstreamer-video-1.0'],text=True).split()
args=['g++','-O3','-DNDEBUG','-fPIC','-shared','-std=c++14',str(stage/'native_pixels.cpp'),'-o',str(stage/'libaura_pixels.so'),'-I/usr/include/opencv4','-lopencv_core','-lopencv_imgproc',*flags]
r=subprocess.run(args,capture_output=True,text=True,timeout=60)
report={'stage':str(stage),'command':args,'code':r.returncode,'output':r.stdout+r.stderr}
(stage/'compile.json').write_text(json.dumps(report,indent=2));print(json.dumps(report))
'''.replace('FILES',repr(files),1)
r=json.loads(ssh('python3 -B -',remote,timeout=80));(HERE/'compile.json').write_text(json.dumps(r,indent=2),encoding='utf-8');print(json.dumps(r));assert r['code']==0
