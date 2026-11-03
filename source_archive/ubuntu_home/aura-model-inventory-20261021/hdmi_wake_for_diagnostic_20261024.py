import json,os,subprocess,time
from pathlib import Path
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()=='89d53e38-4726-4c94-b958-53f2dfb3bd4e'
env=dict(os.environ,DISPLAY=':0')
p=subprocess.run(['xset','dpms','force','on'],capture_output=True,text=True,timeout=8,env=env)
assert p.returncode==0,p.stderr
time.sleep(.5)
q=subprocess.run(['xset','q'],capture_output=True,text=True,timeout=8,env=env)
print(json.dumps({'scope':'wake existing X display for bounded diagnostics; preserve DPMS timers and services',
 'exit_code':p.returncode,'xset_query':q.stdout,'dpms':Path('/sys/class/drm/card0-DP-1/dpms').read_text().strip()}))
