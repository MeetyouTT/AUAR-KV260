import sys,json,subprocess,time
from pathlib import Path
sys.path.insert(0,'/home/root/aura-adaptation-20261006/vsrv-source-14da0e60/unpacked')
from common import *
from vsrv_driver import VSRVDriver
guard();check_runtime()
with open_registers() as io:
 driver=VSRVDriver(io,0x14da0e60,BOOT);s=driver.status()
 assert s['flags']==0 and s['lease_left_ms']==0
original=json.loads((ROOT/'baseline-snapshot.json').read_text())
for p,d in original['firmware_hashes'].items():assert hashlib.sha256(Path(p).read_bytes()).hexdigest()==d
vart=Path('/etc/vart.conf').read_text()
assert vart=='firmware: /lib/firmware/xilinx/'+APP+'/'+APP+'.xclbin\n'
current=json.loads(Path('/home/root/aura-realtime-vision-20261007/current.json').read_text())
status=Path(current['run_root'])/'status.json';before=json.loads(status.read_text());time.sleep(3);after=json.loads(status.read_text())
for k in ('capture_frames','detected_frames','display_frames','rendered_frames'):assert after[k]>before[k]
assert after['boot_id']==BOOT and not after['error'] and not after['stopped']
owners=[]
for p in Path('/proc').iterdir():
 if not p.name.isdecimal():continue
 try:
  if any(f.resolve()==Path('/dev/video0') for f in (p/'fd').iterdir()):owners.append(int(p.name))
 except (FileNotFoundError,PermissionError):pass
assert owners==[current['pid']]
display=run(['xset','-display',':0','q'],10);assert 'Monitor is On' in display
kernel=run(['dmesg'],15)[-16000:]
save('final',{'passed':True,'app':active(),'firmware':firmware(),'stop_status':s,'preview_pid':current['pid'],
 'camera_owners':owners,'run_root':current['run_root'],'release':current['release'],'preview_after':after,
 'display_on':True,'official_firmware_unchanged':True,'vart_conf_matches_active_image':True,
 'vart_conf':vart,'vart_conf_update':'DFX_MANAGER_AUTOMATIC_ON_LOAD',
 'zocl_refs':Path('/sys/module/zocl/refcnt').read_text().strip(),'kernel_tail':kernel,
 'physical_reference_valid':False,'visual_following_started':False,'pwm_active_after_test':False})
