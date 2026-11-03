"""Restore the hash-verified preview after the inspected cold boot; motion off."""
import hashlib,json,os,subprocess,time,uuid
from pathlib import Path
root=Path('/home/root/aura-realtime-vision-20261007')
state=json.loads((root/'current.json').read_text())
boot=Path('/proc/sys/kernel/random/boot_id').read_text().strip()
assert boot=='f7a3ff07-fc20-4804-af12-c314a7a1847a' and boot!=state['after']['boot_id']
release=Path(state['release'])
assert release.parent==root/'releases' and not release.is_symlink()
stages=[json.loads(p.read_text()) for p in (root/'staged.json',root/'motion-staged.json') if p.exists()]
matches=[s for s in stages if s['release']==str(release)]
assert len(matches)==1
for name,digest in matches[0]['hashes'].items():
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
assert Path('/dev/video0').exists()
for cmd in [['xset','-display',':0','dpms','force','on'],['xset','-display',':0','s','reset']]:
    subprocess.run(cmd,check=True,timeout=10)
run=root/'runs'/('coldboot-preview-'+uuid.uuid4().hex)
run.mkdir()
(run/'previous-state.json').write_text(json.dumps(state))
env=dict(os.environ,DISPLAY=':0')
with (run/'worker.log').open('ab') as log:
    p=subprocess.Popen(['python3','-u',str(release/'realtime_vision.py'),'--run-root',str(run)],env=env,stdin=subprocess.DEVNULL,stdout=log,stderr=log,start_new_session=True)
(run/'vision.pid').write_text(str(p.pid))
try:
    deadline=time.monotonic()+25
    first=None
    while time.monotonic()<deadline:
        assert p.poll() is None,'Preview exited'
        if (run/'status.json').exists():
            s=json.loads((run/'status.json').read_text())
            assert not s['error'],s['error']
            if s['detector_ready'] and s['detected_frames']>=3 and s['rendered_frames']>=3:
                first=s;break
        time.sleep(.2)
    assert first,'Preview not ready'
    time.sleep(3)
    after=json.loads((run/'status.json').read_text())
    assert after['boot_id']==boot and not after['error'] and not after['stopped'] and p.poll() is None
    assert not after['actuation_authorized'] and not after['motion_command_emitted'] and after['motion_simulation'] is None
    for key in ['capture_frames','detected_frames','rendered_frames']:
        assert after[key]>first[key]
    restored=dict(pid=p.pid,run_root=str(run),release=str(release),scope='VIDEO_PREVIEW_ONLY',
        previous_boot=state['after']['boot_id'],before=first,after=after,
        apps_before=before_apps,apps_after=apps(),passed=True,rollback=False,
        physical_reference_valid=False)
    temporary=root/'current-restore.tmp';temporary.write_text(json.dumps(restored));temporary.replace(root/'current.json')
    print(json.dumps(dict(passed=True,pid=p.pid,boot_id=boot,run_root=str(run),release=str(release),
        scope='VIDEO_PREVIEW_ONLY',before=first,after=after,fpga_modified=False,motion_command_emitted=False)))
except Exception:
    if p.poll() is None:
        p.terminate();p.wait(timeout=10)
    print(json.dumps(dict(passed=False,worker_log=(run/'worker.log').read_text()[-4000:],new_worker_stopped=p.poll() is not None)))
    raise
