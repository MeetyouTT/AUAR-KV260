# USE_SESSION_COMMON
"""Freeze the current state and request normal camera termination; no FPGA or motor command."""
current_guard()
unit=systemd()
assert unit['MainPID']=='229296' and unit['ActiveState']=='active'
assert unit['Restart']=='no' and unit['SendSIGKILL']=='no' and unit['TimeoutStopUSec']=='infinity'
assert unit['KillMode']=='process'
proc=Path('/proc/229296')
assert digest(proc/'cmdline')=='acf3ee123d7674fdea6e90e79252909ca396249c870269169910879d940c27dd'
birth=int((proc/'stat').read_text().rsplit(')',1)[1].split()[19]);assert birth==2474670
assert dpu_users()==[229296]
verify_wide_files()
health=get_json(8790,'/health')
assert health['pid']==229296 and health['camera_error']=='' and health['detector_error']==''
assert health['identity']['ready'] is True and not health['identity']['shutdown_incomplete']
assert firmware()=='kv260-benchmark-b4096.bit.bin'
assert Path('/etc/vart.conf').read_text()=='firmware: /lib/firmware/xilinx/kv260-benchmark-b4096/kv260-benchmark-b4096.xclbin\n'
startup=document(BUSINESS/'startup/config.json')
pins=startup['component_sha256'];assert len(pins)==380
assert all(digest(BUSINESS/'runtime/aura'/path)==sha for path,sha in pins.items())
assert not ROOT.exists() and not ROOT.is_symlink()
ROOT.mkdir(mode=0o700)
before=dict(schema='aura-face-follow-live-session-1',phase='CAMERA_STOP_INTENT',boot=BOOT,
    operator='01a195e4-58a7-72d3-b141-d5d373579f7f',user_requested_motor_follow=True,
    previous_owner_released=True,camera_pid=229296,camera_birth=birth,
    baseline_startup_sha256=STARTUP_SHA,baseline_components=380,
    camera_checkpoint_before_sha256=digest(CHECKPOINT),baseline_service=unit,
    baseline_firmware=firmware(),baseline_vart=Path('/etc/vart.conf').read_text(),
    baseline_fdt_sha256=digest('/sys/firmware/fdt'),motion_commands_sent=0)
benchmark=Path('/lib/firmware/xilinx/kv260-benchmark-b4096')
before['benchmark_file_pins']={str(p):digest(p) for p in benchmark.iterdir() if p.is_file() and p.suffix in ('.bin','.dtbo','.xclbin','.json')}
atomic(ROOT/'baseline.json',before)
with (ROOT/'baseline.fdt').open('xb') as handle:handle.write(read_regular('/sys/firmware/fdt',2000000))
save(before)
result=subprocess.run(['systemctl','stop','--no-block','aura-camera-ui.service'],capture_output=True,text=True,timeout=5)
assert result.returncode==0
end=time.monotonic()+20
while time.monotonic()<end:
    unit=systemd()
    if unit['MainPID']=='0' and unit['ActiveState'] in ('inactive','failed'):break
    time.sleep(.25)
else:
    before['phase']='CAMERA_STOP_PENDING';before['unit']=unit;save(before)
    print(json.dumps(dict(status='CAMERA_STOP_PENDING',unit=unit,platform_changed=False)));raise SystemExit(0)
assert not proc.exists() and not dpu_users()
loaded=checkpoint_ready(229296,birth)
assert loaded['sha256']!=before['camera_checkpoint_before_sha256']
before.update(phase='CAMERA_STOPPED_CHECKPOINT_SEALED',checkpoint_sha256=loaded['sha256'],
    checkpoint_seed=loaded['seed'],checkpoint_auxiliary=loaded['auxiliary'])
atomic(ROOT/'camera-final-checkpoint.json',loaded['document'])
save(before)
print(json.dumps(dict(status=before['phase'],board_session=str(ROOT),checkpoint_sha256=loaded['sha256'],
    checkpoint_seed=loaded['seed'],checkpoint_auxiliary=loaded['auxiliary'],dpu_users=dpu_users(),
    camera_stopped_normally=True,source_components_verified=380,motion_commands_sent=0)))
