"""Terminate only the two orphaned query subprocesses created by this audit."""
import json,os,signal,time,urllib.request,subprocess
from pathlib import Path
out={'queries':[]}
for pid,verb in [(14156,'query'),(14280,'status')]:
    p=Path('/proc')/str(pid)
    if not p.exists():out['queries'].append({'pid':pid,'already_gone':True});continue
    args=(p/'cmdline').read_bytes().decode().strip('\0').split('\0')
    stat=(p/'stat').read_text().split(') ')[1].split()
    expected=any(Path(a).name=='xdputil' for a in args) and args[-1]==verb and int(stat[1])==1
    assert expected,(pid,args,stat[1])
    os.kill(pid,signal.SIGTERM)
    record={'pid':pid,'verb':verb,'terminated_owned_orphan':True}
    until=time.monotonic()+1
    while p.exists() and time.monotonic()<until:time.sleep(.05)
    if p.exists() and (p/'stat').read_text().split(') ')[1][0]!='Z':
        os.kill(pid,signal.SIGKILL);time.sleep(.1);record['kill_required']=True
    record['remaining_running']=p.exists() and (p/'stat').read_text().split(') ')[1][0]!='Z'
    out['queries'].append(record)
out['services']=subprocess.check_output(['systemctl','show','aura-camera-ui.service','aura-avatar-ui.service','-p','MainPID','-p','ActiveState','-p','NRestarts'],text=True)
with urllib.request.urlopen('http://127.0.0.1:8790/health',timeout=3) as r:d=json.load(r)
out['health']={k:d.get(k) for k in ['pid','detection_hz','camera_error','detector_error']}
print(json.dumps(out),flush=True)
