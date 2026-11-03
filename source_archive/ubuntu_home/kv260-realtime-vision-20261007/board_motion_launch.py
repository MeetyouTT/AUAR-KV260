"""Upgrade our owned preview to SIM control; restore its release on failure."""
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import time
import uuid

ROOT = Path('/home/root/aura-realtime-vision-20261007')
staged = json.loads((ROOT/'motion-staged.json').read_text())
old = json.loads((ROOT/'current.json').read_text())
boot = Path('/proc/sys/kernel/random/boot_id').read_text().strip()
base = staged['base']
assert boot == base['boot_id'], 'Boot changed after read-only inventory'
assert old['pid'] == base['pid'] and old['release'] == base['current_release'], 'Preview changed'
release, old_release = Path(staged['release']), Path(old['release'])
assert release.parent == old_release.parent == ROOT/'releases'
for directory, hashes in [(release, staged['hashes']), (old_release, base['hashes'])]:
    for name, digest in hashes.items():
        assert '/' not in name and hashlib.sha256((directory/name).read_bytes()).hexdigest() == digest
old_status = json.loads((Path(old['run_root'])/'status.json').read_text())
assert old_status['boot_id'] == boot and not old_status['error'] and not old_status['stopped']


def alive(pid):
    try:
        return bool((Path('/proc')/str(pid)/'cmdline').read_bytes())
    except FileNotFoundError:
        return False


def owned(pid, script):
    return alive(pid) and str(script).encode() in (Path('/proc')/str(pid)/'cmdline').read_bytes().split(b'\0')


def stop_owned(pid, script):
    assert owned(pid, script), 'Unknown process left untouched'
    os.kill(pid, signal.SIGTERM)
    deadline = time.monotonic()+10
    while alive(pid) and time.monotonic() < deadline:
        time.sleep(.1)
    assert not alive(pid), 'Owned process did not stop'


def owners():
    found = []
    for proc in Path('/proc').iterdir():
        if not proc.name.isdecimal():
            continue
        try:
            if any(fd.resolve() == Path('/dev/video0') for fd in (proc/'fd').iterdir()):
                found.append(int(proc.name))
        except (FileNotFoundError, PermissionError):
            pass
    return found


def apps():
    p = subprocess.run(['xmutil','listapps'],capture_output=True,text=True,timeout=10)
    rows = [r for r in p.stdout.splitlines() if r.split() and r.split()[0]=='kv260-benchmark-b4096']
    assert p.returncode == 0 and len(rows)==1 and rows[0].split()[-1].rstrip(',')=='0'
    return p.stdout


def spawn(directory, run, simulate):
    run.mkdir(parents=True,exist_ok=False)
    command = ['python3','-u',str(directory/'realtime_vision.py'),'--run-root',str(run)]
    if simulate:
        command.append('--motion-sim')
    with (run/'worker.log').open('ab') as log:
        p = subprocess.Popen(command,env=dict(os.environ,DISPLAY=':0'),stdin=subprocess.DEVNULL,
                             stdout=log,stderr=log,start_new_session=True)
    (run/'vision.pid').write_text(str(p.pid))
    return p


def verify(process, run, simulate):
    first = None
    deadline = time.monotonic()+22
    while time.monotonic() < deadline:
        assert process.poll() is None, 'Preview process exited'
        if (run/'status.json').exists():
            s = json.loads((run/'status.json').read_text())
            assert not s['error'] and not s['stopped'], s['error']
            if s['detector_ready'] and s['detected_frames']>=3 and s['rendered_frames']>=3:
                first = s
                break
        time.sleep(.2)
    assert first, 'Preview did not become ready'
    time.sleep(3)
    second = json.loads((run/'status.json').read_text())
    assert process.poll() is None and not second['error'] and not second['stopped']
    assert second['boot_id']==boot and second['pid']==process.pid
    assert all(second[k]>first[k] for k in ['capture_frames','detected_frames','display_frames','rendered_frames'])
    assert owners()==[process.pid], 'Unexpected camera owner'
    assert not second['motion_command_emitted'] and not second['actuation_authorized']
    if simulate:
        assert second['motion_simulation']['scope']=='SIMULATED'
        assert not second['motion_simulation']['physical_actuation_authorized']
    display = subprocess.run(['xset','-display',':0','q'],capture_output=True,text=True,timeout=10)
    assert display.returncode==0 and 'Monitor is On' in display.stdout
    return first, second


assert owned(old['pid'],old_release/'realtime_vision.py') and owners()==[old['pid']]
apps_before = apps()
run = ROOT/'runs'/('motion-sim-'+uuid.uuid4().hex)
process = None
stopped_old = False
try:
    stop_owned(old['pid'],old_release/'realtime_vision.py')
    stopped_old = True
    assert not owners(), 'Camera occupied after owned preview stop'
    process = spawn(release,run,True)
    (run/'previous-current.json').write_text(json.dumps(old,indent=2))
    first, second = verify(process,run,True)
    state = {'passed':True,'release':str(release),'run_root':str(run),'pid':process.pid,
             'boot_id':boot,'old_pid':old['pid'],'before':first,'after':second,
             'apps_before':apps_before,'apps_after':apps(),'files':staged['hashes'],
             'scope':'SIMULATED','rollback':False,'motion_command_emitted':False,'fpga_modified':False}
    temporary = ROOT/'current.motion.tmp'
    temporary.write_text(json.dumps(state,indent=2))
    temporary.replace(ROOT/'current.json')
    print(json.dumps(state))
except Exception as exc:
    if process and owned(process.pid,release/'realtime_vision.py'):
        stop_owned(process.pid,release/'realtime_vision.py')
    failure = {'passed':False,'error':str(exc),'rollback':stopped_old,'motion_command_emitted':False,
               'fpga_modified':False,'run_root':str(run)}
    if stopped_old:
        assert not owners(), 'Camera occupied; did not start competing fallback'
        rollback_run = ROOT/'runs'/('rollback-'+uuid.uuid4().hex)
        simulate_old = old_status.get('motion_simulation') is not None
        restored = spawn(old_release,rollback_run,simulate_old)
        first, second = verify(restored,rollback_run,simulate_old)
        recovered = dict(old,release=str(old_release),run_root=str(rollback_run),pid=restored.pid,
                         before=first,after=second,rollback=True,boot_id=boot)
        temporary = ROOT/'current.motion.tmp'
        temporary.write_text(json.dumps(recovered,indent=2))
        temporary.replace(ROOT/'current.json')
        failure.update(previous_preview_restored=True,rollback_pid=restored.pid)
    if run.exists():
        (run/'motion-launch-failure.json').write_text(json.dumps(failure,indent=2))
    print(json.dumps(failure))
    raise
