"""Build a bounded, private headless helper; never edits production services."""
import base64, gzip, hashlib, json
from pathlib import Path

HERE=Path(__file__).resolve().parent
names=('tools/idle_body_compositor.py','tools/realtime_facials.py','tools/native_pixels.py')
candidate={n:base64.b64encode((HERE/'candidate/aura'/n).read_bytes()).decode() for n in names}
candidate_pins={n:hashlib.sha256((HERE/'candidate/aura'/n).read_bytes()).hexdigest() for n in names}
candidate_pins['tools/native_pixels.cpp']=hashlib.sha256((HERE/'candidate/aura/tools/native_pixels.cpp').read_bytes()).hexdigest()
pins={'aura/'+n:hashlib.sha256((HERE/'baseline/aura'/n).read_bytes()).hexdigest() for n in
      ('tools/idle_body_compositor.py','tools/realtime_facials.py','tools/native_pixels.py','tools/facial_layers.py',
       'tools/realtime_controller.py','tools/streaming_controller.py','tools/board_avatar_worker.py',
       'board/interaction/avatar_player.py')}
for name,row in json.loads((HERE/'native-source-proof.json').read_text())['files'].items():pins[name]=row['sha256']
prefix='BASELINE_PINS='+repr(pins)+'\nCANDIDATE='+repr(candidate)+'\nCANDIDATE_PINS='+repr(candidate_pins)+'\n'
raw=(prefix+(HERE/'compare_exact.py').read_text()).encode();sha=hashlib.sha256(raw).hexdigest()
cpp=(HERE/'candidate/aura/tools/native_pixels.cpp').read_bytes()
wrapper='PAYLOAD='+repr(base64.b64encode(gzip.compress(raw,mtime=0)).decode())+'\nSOURCE_SHA='+repr(sha)+'\nCPP='+repr(base64.b64encode(cpp).decode())+'\n'+r'''
import base64,gzip,hashlib,json,os,subprocess,sys,time
from pathlib import Path
raw=gzip.decompress(base64.b64decode(PAYLOAD));assert hashlib.sha256(raw).hexdigest()==SOURCE_SHA
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()=='7924ac9f-311d-4fcd-98be-57bf023cf1aa'
assert hashlib.sha256(Path('/etc/systemd/system/aura-camera-ui.service').read_bytes()).hexdigest()=='29786434df9bb9b94a8e640a7a48db47019c224d3876037ce27d3467bb2f5512'
root=Path('/home/root/aura-gui-cpu-20261023')/SOURCE_SHA[:16];root.mkdir(parents=True,exist_ok=True,mode=0o700)
PROFILE_OUTPUT=root
source=Path(sys._getframe().f_code.co_filename).resolve()
args=sys.argv[1:];assert args in ([],['--run'],['--child'])
if args==['--run']:exec(compile(raw,'exact-visual-comparison','exec'))
elif args==['--child']:
 assert not (root/'done.json').exists()
 code=1;output=error=''
 try:
  cpp=root/'native_pixels.cpp';cpp.write_bytes(base64.b64decode(CPP))
  flags=subprocess.check_output(['pkg-config','--cflags','--libs','gstreamer-app-1.0','gstreamer-video-1.0'],text=True).split()
  command=['g++','-O3','-DNDEBUG','-fPIC','-shared','-std=c++14',str(cpp),'-o',str(root/'libaura_pixels.so'),'-I/usr/include/opencv4','-lopencv_core','-lopencv_imgproc',*flags]
  begin=time.monotonic();r=subprocess.run(command,capture_output=True,text=True,timeout=45)
  (root/'compile.json').write_text(json.dumps({'command':command,'exit_code':r.returncode,'seconds':time.monotonic()-begin,'log':r.stdout+r.stderr}))
  assert r.returncode==0,r.stderr
  r=subprocess.run(['/usr/bin/python3','-B',str(source),'--run'],capture_output=True,text=True,timeout=155)
  output,error,code=r.stdout,r.stderr,r.returncode
 except subprocess.TimeoutExpired as exc:
  output,error,code=exc.stdout or '',exc.stderr or '',124
  if isinstance(output,bytes):output=output.decode(errors='replace')
  if isinstance(error,bytes):error=error.decode(errors='replace')
  error+='
EXACT_COMPARISON_TIMEOUT'
 except Exception as exc:
  error=type(exc).__name__+': '+str(exc)
 (root/'stdout.json').write_text(output);(root/'stderr.log').write_text(error)
 (root/'done.json').write_text(json.dumps({'exit_code':code}))
else:
 assert not (root/'done.json').exists(),'Do not overwrite an experiment'
 unit='aura-gui-exact-'+SOURCE_SHA[:16]
 r=subprocess.run(['systemd-run','--unit='+unit,'--property=RuntimeMaxSec=210','--property=Nice=19',
  '--property=CPUQuota=75%','/usr/bin/python3','-B',str(source),'--child'],capture_output=True,text=True,timeout=8)
 assert r.returncode==0,r.stderr
 print(json.dumps({'started':True,'root':str(root),'unit':unit,'source_sha256':SOURCE_SHA,'cpu_quota_percent_one_core':75,'nice':19}))
'''
# Keep the wrapper's literal newline escape in its string valid Python.
wrapper=wrapper.replace("error+='\nEXACT_COMPARISON_TIMEOUT'", "error+='\\nEXACT_COMPARISON_TIMEOUT'")
compile(wrapper,'exact_helper.py','exec')
(HERE/'exact_helper.py').write_text(wrapper)
(HERE/'exact-identity.json').write_text(json.dumps({'source_sha256':sha,'helper_sha256':hashlib.sha256(wrapper.encode()).hexdigest(),'candidate_pins':candidate_pins,'baseline_pins':pins},indent=2)+'\n')
print(sha)
