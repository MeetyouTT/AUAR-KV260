import hashlib,json,subprocess,time
from pathlib import Path
B=Path('/home/root/aura-board-business-20261030/production-5259eab11e42af13');S=B/'startup/config.json'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()=='a6d4a069-e9b0-4065-8df7-dc23556b168e'
startup_sha=sha(S)
p=subprocess.run(['systemctl','show','aura-avatar-ui.service','--property=MainPID'],capture_output=True,text=True,timeout=3)
gui_pid=int(p.stdout.strip().split('=',1)[1]);owners=[]
for proc in Path('/proc').iterdir():
    if not proc.name.isdigit():continue
    try:
        st=(proc/'stat').read_text().rsplit(')',1)[1].split();ppid=int(st[1]);pid=int(proc.name)
        if pid==gui_pid or ppid==gui_pid:
            cmd=(proc/'cmdline').read_bytes();owners.append(dict(pid=pid,ppid=ppid,birth=st[19],cmd_sha256=hashlib.sha256(cmd).hexdigest()))
    except (FileNotFoundError,ProcessLookupError):pass
ui=json.loads((B/'runtime/aura/config/board_avatar_gtk.json').read_bytes())
selected=json.loads(Path(ui['board_business']['face_readback']['path']).read_bytes())
run=Path(selected['camera_config']);cfg=json.loads(run.read_bytes());native=cfg.get('native_execution') or {}
release=Path('/home/root/aura-pan-wide-20261028/release-6a4b645a5bbfd35c')
manifest=release/'candidate-manifest.json'
value=json.loads(manifest.read_bytes())
print(json.dumps(dict(observed_monotonic_ms=round(time.monotonic()*1000),boot_id='a6d4a069-e9b0-4065-8df7-dc23556b168e',
    startup_sha256=startup_sha,startup_unchanged=startup_sha==sha(S),gui_family=owners,
    current_camera_run=dict(path=str(run),sha256=sha(run),native_execution_config=native),
    original_release=dict(root=str(release),manifest_sha256=sha(manifest),bench_identity_stop_sha256=sha(release/'bench_identity_stop.py'),
        runtime_files=value.get('runtime_files'),manifest_keys=sorted(value)),
    board_mutations=False,commands_sent=False,checkpoint_seed_counter_marker_read_or_changed=False)))
