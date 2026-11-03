"""Independent new-boot STOP readback, immutable hashes and preview verification."""
import sys,json,hashlib,time
from pathlib import Path
BOOT='c2753755-e758-4ab6-a4b6-2929271aa723'
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==BOOT
root=Path('/home/root/aura-adaptation-20261006/vsrv-source-14da0e60/unpacked')
assert hashlib.sha256((root/'common.py').read_bytes()).hexdigest()=='f529550d981a6114b669353db08c05174a6e45221c6385456d40896c18b0cc4a'
sys.path.insert(0,str(root));import common
common.BOOT=BOOT;common.guard();common.check_runtime()
from vsrv_driver import VSRVDriver
with common.open_registers() as io:
 s=VSRVDriver(io,0x14da0e60,BOOT).status()
 assert s['flags']==0 and s['lease_left_ms']==0 and not s['active'] and not s['armed']
old=json.loads((root/'baseline-snapshot.json').read_text())
for p,d in old['firmware_hashes'].items():assert hashlib.sha256(Path(p).read_bytes()).hexdigest()==d
assert Path('/etc/vart.conf').read_text()=='firmware: /lib/firmware/xilinx/'+common.APP+'/'+common.APP+'.xclbin\n'
preview=Path('/home/root/aura-realtime-vision-20261007');c=json.loads((preview/'current.json').read_text())
p=Path(c['run_root'])/'status.json';before=json.loads(p.read_text());time.sleep(3);after=json.loads(p.read_text())
for k in ('capture_frames','detected_frames','display_frames','rendered_frames'):assert after[k]>before[k]
assert after['boot_id']==BOOT and not after['error'] and not after['stopped'] and after['mirror_horizontal']
assert not after['actuation_authorized'] and not after['motion_command_emitted']
owners=[]
for proc in Path('/proc').iterdir():
 if not proc.name.isdecimal():continue
 try:
  if any(f.resolve()==Path('/dev/video0') for f in (proc/'fd').iterdir()):owners.append(int(proc.name))
 except (FileNotFoundError,PermissionError):pass
assert owners==[c['pid']]
display=common.run(['xset','-display',':0','q'],10);assert 'Monitor is On' in display
print(json.dumps({'passed':True,'boot_id':BOOT,'app':common.active(),'firmware':common.firmware(),'stop_status':s,'preview_pid':c['pid'],'camera_owners':owners,'run_root':c['run_root'],'release':c['release'],'after':after,'display_on':True,'official_firmware_unchanged':True,'physical_reference_valid':False,'pwm_active_after_test':False}))
