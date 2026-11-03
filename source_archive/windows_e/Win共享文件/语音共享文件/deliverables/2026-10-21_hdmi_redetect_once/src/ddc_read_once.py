"""One standard EDID read on the already identified DP AUX I2C adapter."""
import hashlib,json,os,subprocess,time
from pathlib import Path
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()=='5cd17bb7-30da-4a4f-bf18-8167508de1f4'
assert Path('/sys/class/i2c-adapter/i2c-2/name').read_text().strip()=='ZynqMP DP AUX'
assert Path('/sys/block/mmcblk1/device/cid').read_text().strip()=='0353445345333247805558c00401a100'
root=Path('/run/aura-hdmi-redetect-once-5cd17bb7-30da-4a4f-bf18-8167508de1f4')
record=root/'ddc-read.json'
assert root.is_dir() and not record.exists()
p=Path('/sys/class/drm/card0-DP-1/edid')
before=p.read_bytes();assert not before
def units():return subprocess.check_output(['systemctl','show','aura-avatar-ui.service','aura-camera-ui.service','xserver-nodm.service','-p','Id','-p','MainPID','-p','ActiveState','-p','NRestarts'],text=True,timeout=4)
v={'operation':'one_standard_edid_read','bus':2,'address':'0x50','offset':0,'read_bytes_requested':128,'system_bus_1_accessed':False,'register_configuration_writes':0,'edid_offset_pointer_set':True,'movement_commands_sent':0,'display_modesets_sent':0,'units_before':units()}
with record.open('x') as f:json.dump({'started':True},f)
started=time.monotonic()
try:
 q=subprocess.run(['/usr/sbin/i2ctransfer','-y','2','w1@0x50','0x00','r128'],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,timeout=6)
 v['exit_code']=q.returncode;v['stderr']=q.stderr[-1000:]
 if q.returncode==0:
  raw=bytes(int(x,16) for x in q.stdout.split())
  v['edid_bytes_read']=len(raw);v['edid_sha256']=hashlib.sha256(raw).hexdigest()
  v['edid_valid']=len(raw)==128 and raw[:8]==b'\x00\xff\xff\xff\xff\xff\xff\x00' and sum(raw)%256==0
except subprocess.TimeoutExpired:v['error']='timeout'
v['elapsed_seconds']=round(time.monotonic()-started,3)
v['sysfs_edid_bytes_after']=len(p.read_bytes());v['units_after']=units()
v['units_unchanged']=v['units_before']==v['units_after']
record.write_text(json.dumps(v,indent=2)+'\n')
print(json.dumps(v),flush=True)
