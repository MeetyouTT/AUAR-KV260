# USE_SESSION_COMMON
"""Finish verification after xmutil itself updated VART; never repeats platform loading."""
current_guard()
j=state();assert j['phase']=='WIDE_LOAD_INTENT'
assert j['unload_returncode']==0 and j['load_returncode']==0
assert systemd()['MainPID']=='0' and not dpu_users()
assert checkpoint_ready(j['camera_pid'],j['camera_birth'])['sha256']==j['checkpoint_sha256']
wide_active();verify_wide_files()
j.update(phase='WIDE_ACTIVE_NO_CAMERA_NO_MOTION',wide_fdt_sha256=digest('/sys/firmware/fdt'),
    wide_vart_sha256=digest('/etc/vart.conf'),wide_firmware=firmware(),
    vart_updated_by_existing_platform_loader=True);save(j)
print(json.dumps(dict(status=j['phase'],firmware=firmware(),fdt_sha256=j['wide_fdt_sha256'],
    vart_exact_wide=True,fpga_operating=True,dpu_users=dpu_users(),
    platform_load_repeated=False,vart_updated_by_xmutil=True,motion_commands_sent=0)))
