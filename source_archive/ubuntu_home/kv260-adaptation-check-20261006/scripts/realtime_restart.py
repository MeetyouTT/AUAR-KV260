"""Restart the owned preview."""
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import time
import uuid

root = Path('/home/root/aura-realtime-vision-20261007')
state = json.loads((root/'current.json').read_text())
simulated = state.get('scope')=='SIMULATED'
staged = json.loads((root/('motion-staged.json' if simulated else 'staged.json')).read_text())
release = Path(state['release'])
assert release.parent == root/'releases' and str(release)==staged['release']
boot = Path('/proc/sys/kernel/random/boot_id').read_text().strip()
assert boot==state['after']['boot_id'], 'Recheck inventory after a board reboot'
for name,digest in staged['hashes'].items():
    assert '/' not in name and hashlib.sha256((release/name).read_bytes()).hexdigest()==digest
script = str(release/'realtime_vision.py')
old_pid = state['pid']

def alive(pid):
    p = Path('/proc')/str(pid)/'cmdline'
    return p.exists() and bool(p.read_bytes())

def stop_owned(pid,expected):
    assert alive(pid) and expected.encode() in (Path('/proc')/str(pid)/'cmdline').read_bytes().split(b'\0')
    os.kill(pid,signal.SIGTERM)
    deadline = time.monotonic()+10
    while alive(pid) and time.monotonic()<deadline:
        time.sleep(.1)
    assert not alive(pid)

def apps():
    p = subprocess.run(['xmutil','listapps'],capture_output=True,text=True,timeout=10)
    assert p.returncode==0
    row = next(r for r in p.stdout.splitlines() if r.split() and r.split()[0]=='kv260-benchmark-b4096')
    assert row.split()[-1].rstrip(',')=='0'
    return p.stdout

assert alive(old_pid)
assert script.encode() in (Path('/proc')/str(old_pid)/'cmdline').read_bytes().split(b'\0')
before_apps = apps()
run = root/'runs'/('restart-'+uuid.uuid4().hex)
run.mkdir()
(run/'previous-state.json').write_text(json.dumps(state,indent=2))
subprocess.run(['xset','-display',':0','dpms','force','on'],check=True,timeout=10)
stop_owned(old_pid,script)
process = None
try:
    with (run/'worker.log').open('ab') as log:
        command = ['python3','-u',script,'--run-root',str(run)]+(['--motion-sim'] if simulated else [])
        process = subprocess.Popen(command,env=dict(os.environ,DISPLAY=':0'),stdin=subprocess.DEVNULL,stdout=log,stderr=log,start_new_session=True)
    (run/'vision.pid').write_text(str(process.pid))
    deadline = time.monotonic()+20
    first = None
    while time.monotonic()<deadline:
        assert process.poll() is None, 'Preview exited'
        if (run/'status.json').exists():
            s = json.loads((run/'status.json').read_text())
            assert not s['error'],s['error']
            if s['detector_ready'] and s['detected_frames']>=3 and s['rendered_frames']>=3:
                first = s
                break
        time.sleep(.2)
    assert first,'Preview not ready'
    time.sleep(3)
    after = json.loads((run/'status.json').read_text())
    assert not after['error'] and not after['stopped'] and process.poll() is None
    for key in ['capture_frames','detected_frames','display_frames','rendered_frames']:
        assert after[key]>first[key],key
    state.update(pid=process.pid,run_root=str(run),restarted_from_pid=old_pid,before=first,after=after,apps_before=before_apps,apps_after=apps(),passed=True,rollback=False)
    tmp = root/'current-restart.tmp'
    tmp.write_text(json.dumps(state,indent=2))
    tmp.replace(root/'current.json')
    print(json.dumps(state))
except Exception as exc:
    if process and alive(process.pid):
        stop_owned(process.pid,script)
    old = Path('/home/root/aura-camera-check-20261006')
    with (old/'fullscreen.log').open('ab') as log:
        p = subprocess.Popen(['python3','-u',str(old/'fullscreen_preview.py')],env=dict(os.environ,DISPLAY=':0'),stdin=subprocess.DEVNULL,stdout=log,stderr=log,start_new_session=True)
    (old/'preview.pid').write_text(str(p.pid))
    time.sleep(3)
    a = json.loads((old/'fullscreen-status.json').read_text())
    time.sleep(2)
    b = json.loads((old/'fullscreen-status.json').read_text())
    print(json.dumps({'passed':False,'error':str(exc),'run_root':str(run),'rollback_pid':p.pid,'restored':p.poll() is None and b['frames']>a['frames'] and b['error'] is None}))
    raise
