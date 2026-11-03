"""Restore the validated preview on the newly inventoried, idle board."""
import hashlib,json,os,signal,subprocess,time,uuid
from pathlib import Path
root=Path('/home/root/aura-realtime-vision-20261007')
state=json.loads((root/'current.json').read_text())
staged=json.loads((root/'staged.json').read_text())
boot=Path('/proc/sys/kernel/random/boot_id').read_text().strip()
assert boot=='4365d744-ddef-4325-a264-e7bb57cc9bb8' and boot!=state['after']['boot_id']
release=Path(state['release'])
assert release.parent==root/'releases' and str(release)==staged['release']
for name,digest in staged['hashes'].items():
    assert '/' not in name and hashlib.sha256((release/name).read_bytes()).hexdigest()==digest
for proc in Path('/proc').iterdir():
    if proc.name.isdecimal():
        try:
            assert not any(fd.resolve()==Path('/dev/video0') for fd in (proc/'fd').iterdir()),'Camera already owned'
        except (FileNotFoundError,PermissionError):
            pass
def apps():
    p=subprocess.run(['xmutil','listapps'],capture_output=True,text=True,timeout=10)
    assert p.returncode==0
    row=next(r for r in p.stdout.splitlines() if r.split() and r.split()[0]=='kv260-benchmark-b4096')
    assert row.split()[-1].rstrip(',')=='0'
    return p.stdout
before_apps=apps()
for cmd in [['xset','-display',':0','dpms','force','on'],['xset','-display',':0','s','reset']]:
    subprocess.run(cmd,check=True,timeout=10)
run=root/'runs'/('restore-'+uuid.uuid4().hex)
run.mkdir()
(run/'previous-state.json').write_text(json.dumps(state))
env=dict(os.environ,DISPLAY=':0')
with (run/'worker.log').open('ab') as log:
    p=subprocess.Popen(['python3','-u',str(release/'realtime_vision.py'),'--run-root',str(run)],env=env,stdin=subprocess.DEVNULL,stdout=log,stderr=log,start_new_session=True)
(run/'vision.pid').write_text(str(p.pid))
try:
    deadline=time.monotonic()+20
    first=None
    while time.monotonic()<deadline:
        assert p.poll() is None,'Preview exited'
        if (run/'status.json').exists():
            s=json.loads((run/'status.json').read_text())
            assert not s['error'],s['error']
            if s['detector_ready'] and s['detected_frames']>=3 and s['rendered_frames']>=3:
                first=s
                break
        time.sleep(.2)
    assert first,'Preview not ready'
    time.sleep(3)
    after=json.loads((run/'status.json').read_text())
    assert not after['error'] and not after['stopped'] and p.poll() is None
    for key in ['capture_frames','detected_frames','rendered_frames']:
        assert after[key]>first[key]
    state.update(pid=p.pid,run_root=str(run),previous_boot=state['after']['boot_id'],before=first,after=after,apps_before=before_apps,apps_after=apps(),passed=True,rollback=False)
    temporary=root/'current-restore.tmp'
    temporary.write_text(json.dumps(state))
    temporary.replace(root/'current.json')
    print(json.dumps({'passed':True,'pid':p.pid,'boot':boot,'run_root':str(run),'before':first,'after':after,'fpga_modified':False,'motion_command_emitted':False}))
except Exception:
    if p.poll() is None:
        p.terminate()
        p.wait(timeout=10)
    old=Path('/home/root/aura-camera-check-20261006')
    with (old/'fullscreen.log').open('ab') as log:
        fallback=subprocess.Popen(['python3','-u',str(old/'fullscreen_preview.py')],env=env,stdin=subprocess.DEVNULL,stdout=log,stderr=log,start_new_session=True)
    (old/'preview.pid').write_text(str(fallback.pid))
    time.sleep(3)
    a=json.loads((old/'fullscreen-status.json').read_text())
    time.sleep(2)
    b=json.loads((old/'fullscreen-status.json').read_text())
    print(json.dumps({'passed':False,'rollback_pid':fallback.pid,'restored':fallback.poll() is None and b['frames']>a['frames'] and not b['error'],'worker_log':(run/'worker.log').read_text()}))
    raise
