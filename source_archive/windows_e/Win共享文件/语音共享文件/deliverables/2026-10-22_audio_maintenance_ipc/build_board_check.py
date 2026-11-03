"""Stage only isolated source/tests, then run owned synthetic subprocesses."""
import ast
import base64
import gzip
import hashlib
import io
import json
from pathlib import Path
import tarfile

ROOT=Path(__file__).resolve().parent
files=list(sorted((ROOT/'candidate').rglob('*.py')))
files += [ROOT/'test_maintenance_ipc.py',ROOT/'recovered/tools/board_avatar_worker.py']
manifest={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
target=Path('/home/ghmd/aura-identity-dpu-check-20261018/board_audio_maintenance_ipc_20261022.py')
buffer=io.BytesIO()
with tarfile.open(fileobj=buffer,mode='w',format=tarfile.PAX_FORMAT) as tar:
    for p in files:
        raw=p.read_bytes();info=tarfile.TarInfo(str(p.relative_to(ROOT)))
        info.size=len(raw);info.mode=0o600;info.mtime=0;tar.addfile(info,io.BytesIO(raw))
payload=gzip.compress(buffer.getvalue(),mtime=0)
if target.exists():
    # Preserve the exact first accepted gzip stream (including its header).
    tree=ast.parse(target.read_text())
    assignment=next(n for n in tree.body if isinstance(n,ast.Assign)
        and any(isinstance(t,ast.Name) and t.id=='PAYLOAD' for t in n.targets))
    payload=base64.b64decode(ast.literal_eval(assignment.value))
    with tarfile.open(fileobj=io.BytesIO(payload),mode='r:gz') as archive:
        assert set(archive.getnames())==set(manifest)
        for name,digest in manifest.items():
            assert hashlib.sha256(archive.extractfile(name).read()).hexdigest()==digest
digest=hashlib.sha256(payload).hexdigest()
base=Path('/home/ghmd/aura-audio-recovery-20261021/live-source/tools')
original={name:hashlib.sha256((base/name).read_bytes()).hexdigest() for name in
    ('board_avatar_gtk.py','gstreamer_audio_worker.py','gstreamer_audio.py',
     'gstreamer_audio_engine.py','gstreamer_persistent_engine.py','realtime_audio.py')}
prefix='PAYLOAD=%r\nDIGEST=%r\nMANIFEST=%r\nORIGINAL=%r\n' % (
    base64.b64encode(payload).decode(),digest,manifest,original)
body=r'''
import base64,hashlib,io,json,os,signal,subprocess,sys,tarfile,time,urllib.request
from pathlib import Path
EXPECTED_BOOT='215c4292-ce84-4828-9827-83c32ba66564'
LIVE=Path('/home/root/aura-speech-motion-20261021/de989bf024a9/runtime/aura')
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==EXPECTED_BOOT
for name,digest in ORIGINAL.items():assert hashlib.sha256((LIVE/'tools'/name).read_bytes()).hexdigest()==digest,name
op=urllib.request.build_opener(urllib.request.ProxyHandler({}))
def get(port,path):
    with op.open('http://127.0.0.1:'+str(port)+path,timeout=3) as f:return json.load(f)
def health():
    s=get(8790,'/health');u=get(8783,'/api/state')
    units={}
    for name in ('aura-avatar-ui.service','aura-camera-ui.service','xserver-nodm.service'):
        units[name]=subprocess.check_output(['systemctl','show',name,'-p','MainPID','--value'],timeout=3).decode().strip()
    return dict(camera={k:s.get(k) for k in ('pid','detected_frames','camera_error','detector_error')},
        units=units,ui={k:u.get(k) for k in ('phase','playing','paused','audio_output_state')},
        backend=s.get('identity',{}).get('face_targets',{}).get('backend'))
def kernel():
    raw=subprocess.check_output(['journalctl','-k','-n','2000','-o','json','--no-pager'],timeout=5).decode()
    return [json.loads(line) for line in raw.splitlines() if line.strip()]
before=health();logs=kernel();before_mono=time.monotonic()
assert before['units']=={'aura-avatar-ui.service':'215734','aura-camera-ui.service':'264975','xserver-nodm.service':'1077'}
assert before['backend']=='DPU_YUNET_INT8'
assert before['ui']['phase']=='IDLE' and not before['ui']['playing'] and not before['ui']['paused']
raw=base64.b64decode(PAYLOAD);assert hashlib.sha256(raw).hexdigest()==DIGEST
root=Path('/home/root/aura-audio-maintenance-ipc-20261022')/DIGEST[:16]
root.mkdir(parents=True,exist_ok=True);assert not root.is_symlink()
with tarfile.open(fileobj=io.BytesIO(raw),mode='r:gz') as tar:
    assert len(tar.getmembers())==len(MANIFEST)
    for member in tar.getmembers():
        assert member.isfile() and member.name in MANIFEST
        path=root/member.name;path.parent.mkdir(parents=True,exist_ok=True)
        assert not any(p.is_symlink() for p in (path,*path.parents))
        data=tar.extractfile(member).read();assert hashlib.sha256(data).hexdigest()==MANIFEST[member.name]
        if path.exists():assert path.read_bytes()==data
        else:
            with path.open('xb') as f:f.write(data)
started=time.monotonic()
process=subprocess.Popen([sys.executable,'-B','-m','unittest','-v','test_maintenance_ipc'],
    cwd=str(root),stdout=subprocess.PIPE,stderr=subprocess.STDOUT,start_new_session=True)
try:
    try:output,_=process.communicate(timeout=35)
    except subprocess.TimeoutExpired:
        os.killpg(process.pid,signal.SIGTERM)
        try:output,_=process.communicate(timeout=3)
        except subprocess.TimeoutExpired:
            os.killpg(process.pid,signal.SIGKILL);output,_=process.communicate(timeout=3)
        raise RuntimeError('Owned synthetic test group exceeded deadline')
finally:
    if process.poll() is None:
        os.killpg(process.pid,signal.SIGKILL);process.communicate(timeout=3)
after=health();newlogs=kernel()
covered=not newlogs or int(newlogs[0].get('__MONOTONIC_TIMESTAMP',0))/1e6<=before_mono
warnings=[row for row in newlogs if int(row.get('__MONOTONIC_TIMESTAMP',0))/1e6>=before_mono
          and "WARN: HC couldn't access mem fast enough" in row.get('MESSAGE','')]
assert after['units']==before['units']
assert after['camera']['pid']==before['camera']['pid']
assert after['camera']['detected_frames']>before['camera']['detected_frames']
assert not after['camera']['camera_error'] and not after['camera']['detector_error']
for name,digest in ORIGINAL.items():assert hashlib.sha256((LIVE/'tools'/name).read_bytes()).hexdigest()==digest
result=dict(scope='REAL_BOARD_ISOLATED_IPC_SYNTHETIC_GSTREAMER_ONLY',
    bundle_sha256=DIGEST,source_hashes=MANIFEST,board_python=sys.version.split()[0],
    exit_code=process.returncode,test_output=output.decode(errors='replace'),
    duration_seconds=round(time.monotonic()-started,3),before=before,after=after,
    kernel_window_covered=covered,new_matching_usb_warnings=len(warnings),
    production_sources_unchanged=True,alsa_opened=False,new_camera_or_dpu_owner=False,
    production_gtk_integration_verified=False,mcp01_recovery_verified=False,
    synthetic_visual_resize_stub=True,synthetic_pcm_only=True)
print(json.dumps(result),flush=True)
assert process.returncode==0
assert covered and not warnings
'''
source=prefix+body;ast.parse(source)
if target.exists():assert target.read_text()==source,'Freeze checks; use a new revision after changes'
else:target.write_text(source)
(ROOT/'board-check-manifest.json').write_text(json.dumps({'helper':str(target),
    'helper_sha256':hashlib.sha256(source.encode()).hexdigest(),'bundle_sha256':digest,
    'bundle_bytes':len(payload),'sources':manifest,'original_sources':original},indent=2)+'\n')
print(json.dumps({'helper':str(target),'payload_bytes':len(payload),'helper_bytes':len(source)}))
