"""Replace only our known preview after preflight; restore it on failure."""
import datetime
import json
import os
from pathlib import Path
import signal
import subprocess
import time

ROOT = Path('/home/root/aura-realtime-vision-20261007')
OLD = Path('/home/root/aura-camera-check-20261006')
OLD_SCRIPT = str(OLD/'fullscreen_preview.py')
staged = json.loads((ROOT/'staged.json').read_text())
release = Path(staged['release'])
assert release.parent == ROOT/'releases'
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip() == '5134c246-b23b-48a1-9365-0bb36426d79f'


def alive(pid):
    p = Path('/proc')/str(pid)
    return p.exists() and bool((p/'cmdline').read_bytes())


def owned(pid, script):
    return alive(pid) and script.encode() in (Path('/proc')/str(pid)/'cmdline').read_bytes().split(b'\0')


def stop_owned(pid, script):
    assert owned(pid, script), 'Unexpected process; left untouched'
    os.kill(pid, signal.SIGTERM)
    limit = time.monotonic()+10
    while alive(pid) and time.monotonic()<limit:
        time.sleep(.1)
    assert not alive(pid), 'Owned process did not stop'


def app_state():
    p = subprocess.run(['xmutil','listapps'],capture_output=True,text=True,timeout=10)
    assert p.returncode == 0
    rows = [r for r in p.stdout.splitlines() if r.split() and r.split()[0]=='kv260-benchmark-b4096']
    assert len(rows)==1 and rows[0].split()[-1].rstrip(',')=='0', 'Official active slot changed'
    return p.stdout


old_pid = int((OLD/'preview.pid').read_text())
assert owned(old_pid, OLD_SCRIPT)
apps_before = app_state()
stamp = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')
run = ROOT/'runs'/stamp
run.mkdir(parents=True,exist_ok=False)
env = dict(os.environ, DISPLAY=':0')
subprocess.run(['xset','-display',':0','dpms','force','on'],check=True,timeout=10)
script = str(release/'realtime_vision.py')
process = None
stopped_old = False
try:
    stop_owned(old_pid, OLD_SCRIPT)
    stopped_old = True
    with (run/'worker.log').open('ab') as log:
        process = subprocess.Popen(['python3','-u',script,'--run-root',str(run)],env=env,
                                   stdin=subprocess.DEVNULL,stdout=log,stderr=log,start_new_session=True)
    (run/'vision.pid').write_text(str(process.pid))
    deadline = time.monotonic()+20
    before = None
    while time.monotonic()<deadline:
        assert process.poll() is None, 'Real-time preview exited'
        if (run/'status.json').exists():
            s = json.loads((run/'status.json').read_text())
            assert not s['error'], s['error']
            if s['detector_ready'] and s['detected_frames']>=3 and s['rendered_frames']>=3:
                before = s
                break
        time.sleep(.2)
    assert before, 'Real-time preview did not become ready'
    time.sleep(3)
    after = json.loads((run/'status.json').read_text())
    assert not after['error'] and not after['stopped'] and process.poll() is None
    for key in ['capture_frames','detected_frames','display_frames','rendered_frames']:
        assert after[key]>before[key], key+' stalled'
    apps_after = app_state()
    state = {'passed':True,'release':str(release),'run_root':str(run),'pid':process.pid,
             'old_pid':old_pid,'before':before,'after':after,'apps_before':apps_before,
             'apps_after':apps_after,'rollback':False,'motion_command_emitted':False,'fpga_modified':False}
    (ROOT/'current.json').write_text(json.dumps(state,indent=2))
    print(json.dumps(state,indent=2))
except Exception as exc:
    if process and owned(process.pid,script):
        stop_owned(process.pid,script)
    restored = None
    if stopped_old:
        with (OLD/'fullscreen.log').open('ab') as log:
            fallback = subprocess.Popen(['python3','-u',OLD_SCRIPT],env=env,stdin=subprocess.DEVNULL,
                                        stdout=log,stderr=log,start_new_session=True)
        (OLD/'preview.pid').write_text(str(fallback.pid))
        time.sleep(3)
        first = json.loads((OLD/'fullscreen-status.json').read_text())
        time.sleep(2)
        second = json.loads((OLD/'fullscreen-status.json').read_text())
        restored = fallback.poll() is None and second['frames']>first['frames'] and second['error'] is None
    state = {'passed':False,'error':str(exc),'run_root':str(run),'rollback':stopped_old,
             'old_preview_restored':restored,'worker_log':(run/'worker.log').read_text() if (run/'worker.log').exists() else ''}
    (run/'launch-failure.json').write_text(json.dumps(state,indent=2))
    print(json.dumps(state,indent=2))
    raise
