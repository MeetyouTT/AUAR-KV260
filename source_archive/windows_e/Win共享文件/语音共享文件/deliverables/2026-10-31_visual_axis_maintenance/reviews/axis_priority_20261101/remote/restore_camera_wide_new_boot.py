# USE_SESSION_COMMON
"""Start the unchanged original camera once, consuming only its exact final checkpoint."""
current_guard();wide_active();verify_wide_files()
j=state();assert j['phase'] in ('WIDE_ACTIVE_NO_CAMERA_NO_MOTION','CAMERA_START_PENDING')
if j['phase']=='WIDE_ACTIVE_NO_CAMERA_NO_MOTION':
    assert systemd()['MainPID']=='0' and not dpu_users()
    assert checkpoint_ready(j['camera_pid'],j['camera_birth'])['sha256']==j['checkpoint_sha256']
    j['phase']='CAMERA_START_PENDING';save(j)
    started=subprocess.run(['systemctl','start','--no-block','aura-camera-ui.service'],capture_output=True,text=True,timeout=5)
    assert started.returncode==0
end=time.monotonic()+25
last=None
while time.monotonic()<end:
    unit=systemd();pid=int(unit['MainPID'])
    if pid:
        try:
            last=get_json(8790,'/health')
            if last.get('pid')==pid and last.get('identity',{}).get('ready') is True and not last.get('camera_error') and not last.get('detector_error'):
                break
        except (OSError,ValueError,AssertionError):pass
    if unit['ActiveState']=='failed':break
    time.sleep(.5)
else:unit=systemd();pid=int(unit['MainPID'])
if not (last and last.get('pid')==pid and last.get('identity',{}).get('ready') is True and not last.get('camera_error') and not last.get('detector_error')):
    print(json.dumps(dict(status='CAMERA_START_PENDING_OR_FAILED',unit=unit,health_available=last is not None,
        identity_ready=(last or {}).get('identity',{}).get('ready'),motion_commands_sent=0)));raise SystemExit(0)
proc=Path('/proc')/str(pid)
assert digest(proc/'cmdline')=='acf3ee123d7674fdea6e90e79252909ca396249c870269169910879d940c27dd'
birth=int((proc/'stat').read_text().rsplit(')',1)[1].split()[19])
assert pid!=j['camera_pid'] and dpu_users()==[pid]
audit=document(OPS/'pan-face-edge-v5/native-operator-v1'/('recovery-audit-'+str(pid)+'.json'))
seed=audit['exact_seed_before_operator_request']
assert audit['checkpoint_sha256']==j['checkpoint_sha256']
assert seed==j['checkpoint_seed']
run_config=document(OPS/('native-run-'+BOOT+'-'+str(pid))/'config.json')
assert run_config['native_execution']['seed']['sha256']==j['checkpoint_sha256']
j.update(phase='CAMERA_RESTORED_ON_WIDE',restored_camera_pid=pid,restored_camera_birth=birth,
    restored_camera_command_sha256=digest(proc/'cmdline'),native_seed_preserved=True);save(j)
print(json.dumps(dict(status=j['phase'],camera_pid=pid,camera_birth=birth,
    exact_checkpoint_restored=True,native_seed_preserved=True,
    camera_error=bool(last.get('camera_error')),detector_error=bool(last.get('detector_error')),
    identity_ready=last['identity']['ready'],identity_error=bool(last['identity'].get('error')),
    capture_frames=last.get('capture_frames'),detected_frames=last.get('detected_frames'),
    face_detector_processed=last['identity'].get('face_targets',{}).get('processed'),
    identity_processed=last['identity'].get('processed'),motion_commands_sent=0)))
