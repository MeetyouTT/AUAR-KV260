# USE_SESSION_COMMON
"""Load the paired wide platform only after the sole DPU owner sealed its final checkpoint."""
current_guard()
j=state();assert j['phase']=='CAMERA_STOPPED_CHECKPOINT_SEALED'
assert systemd()['MainPID']=='0' and not dpu_users()
assert checkpoint_ready(j['camera_pid'],j['camera_birth'])['sha256']==j['checkpoint_sha256']
verify_wide_files()
baseline=document(ROOT/'baseline.json')
assert all(digest(path)==sha for path,sha in baseline['benchmark_file_pins'].items())
assert firmware()==baseline['baseline_firmware']
j['phase']='WIDE_UNLOAD_INTENT';save(j)
unload=subprocess.run(['/usr/bin/xmutil','unloadapp'],capture_output=True,text=True,timeout=35)
j['unload_returncode']=unload.returncode;j['unload_output']=unload.stdout[-4000:];save(j)
assert unload.returncode==0
assert not dpu_users()
j['phase']='WIDE_LOAD_INTENT';save(j)
load=subprocess.run(['/usr/bin/xmutil','loadapp',APP],capture_output=True,text=True,timeout=45)
j['load_returncode']=load.returncode;j['load_output']=load.stdout[-4000:];save(j)
assert load.returncode==0
assert firmware()==APP+'.bit.bin'
assert Path('/sys/class/fpga_manager/fpga0/state').read_text().strip()=='operating'
conf=Path('/etc/vart.conf');assert conf.read_text()==baseline['baseline_vart']
tmp=conf.with_name('vart.conf.aura-axis-bebd3e7d-r2.partial')
text='firmware: '+str(FW/(APP+'.xclbin'))+'\n'
fd=os.open(str(tmp),os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o644)
with os.fdopen(fd,'w') as handle:handle.write(text);handle.flush();os.fsync(handle.fileno())
os.replace(str(tmp),str(conf))
wide_active();verify_wide_files()
j.update(phase='WIDE_ACTIVE_NO_CAMERA_NO_MOTION',wide_fdt_sha256=digest('/sys/firmware/fdt'),
    wide_vart_sha256=digest('/etc/vart.conf'),wide_firmware=firmware());save(j)
print(json.dumps(dict(status=j['phase'],firmware=firmware(),fdt_sha256=j['wide_fdt_sha256'],
    vart_exact_wide=True,fpga_operating=True,dpu_users=dpu_users(),
    unload_returncode=unload.returncode,load_returncode=load.returncode,motion_commands_sent=0)))
