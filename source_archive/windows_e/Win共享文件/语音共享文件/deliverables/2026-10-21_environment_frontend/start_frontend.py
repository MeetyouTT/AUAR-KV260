"""Launch the pinned independent CPU service, detached and hidden on Windows."""
import hashlib,json,socket,subprocess,sys,time
from pathlib import Path
HERE=Path(__file__).resolve().parent
AURA=HERE/'pc_service/aura';sys.path.insert(0,str(AURA))
from common.frontend_wire import PROTOCOL,send,receive
def health():
 with socket.create_connection(('192.168.50.1',8795),timeout=1) as c:
  send(c,{'protocol':PROTOCOL,'kind':'health'});meta,pcm=receive(c,1)
  assert not pcm and meta.get('protocol')==PROTOCOL and meta.get('ready') is True
  return meta
for n,sha in json.loads((HERE/'pc_service/manifest.json').read_text(encoding='utf-8-sig')).items():
 assert hashlib.sha256((AURA/n).read_bytes()).hexdigest()==sha,n
try:
 result=health()
 assert (HERE/'frontend_process.json').exists(),'Unowned frontend listener'
 print(json.dumps(result));raise SystemExit(0)
except (OSError,AssertionError,ValueError):pass
# Binding first ensures a foreign listener is never stopped or replaced.
with socket.socket() as check:check.bind(('192.168.50.1',8795))
startup=subprocess.STARTUPINFO();startup.dwFlags|=subprocess.STARTF_USESHOWWINDOW;startup.wShowWindow=0
args=[sys.executable,'-B',str(AURA/'tools/audio_frontend_host.py'),'--models','D:/AIModels/audio-frontend-eval-20261021','--listen','192.168.50.1','--port','8795']
with (HERE/'frontend_stdout.log').open('ab') as out,(HERE/'frontend_stderr.log').open('ab') as err:
 child=subprocess.Popen(args,stdin=subprocess.DEVNULL,stdout=out,stderr=err,cwd=AURA,
  creationflags=0x8|0x200|0x08000000,startupinfo=startup)
(HERE/'frontend_process.json').write_text(json.dumps({'launcher_pid':child.pid,'script':args[2],
 'models':'D:/AIModels/audio-frontend-eval-20261021','port':8795,'launched_unix':time.time()},indent=2)+'\n')
deadline=time.monotonic()+20
while time.monotonic()<deadline:
 if child.poll() is not None:raise RuntimeError('Frontend exited; inspect frontend_stderr.log')
 try:result=health();print(json.dumps(result));break
 except (OSError,AssertionError,ValueError):time.sleep(.25)
else:raise RuntimeError('Frontend readiness deadline')
