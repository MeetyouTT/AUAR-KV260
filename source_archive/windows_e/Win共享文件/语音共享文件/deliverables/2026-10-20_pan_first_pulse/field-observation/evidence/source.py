"""Check STOP after reported physical movement. No ARM/COMMIT or new pulse."""
import hashlib,json,sys,urllib.request
from pathlib import Path
BOOT='3e1add36-b917-4289-91dc-699348528782'
ROOT=Path('/home/root/aura-adaptation-20261006/vsrv-source-14da0e60/unpacked')
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==BOOT
assert hashlib.sha256((ROOT/'common.py').read_bytes()).hexdigest()=='f529550d981a6114b669353db08c05174a6e45221c6385456d40896c18b0cc4a'
sys.path.insert(0,str(ROOT))
import common
common.BOOT=BOOT
common.guard();common.check_runtime()
assert common.active()==[common.APP] and common.firmware()==common.APP+'.bit.bin'
from vsrv_driver import VSRVDriver
with common.open_registers() as io:
 status=VSRVDriver(io,0x14da0e60,BOOT).status()
 assert status['flags']==0 and status['lease_left_ms']==0 and not status['active'] and not status['armed']
opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
with opener.open('http://127.0.0.1:8790/health',timeout=2) as r:health=json.load(r)
print(json.dumps({'status':'DISARMED_AFTER_USER_REPORTED_MOVEMENT','boot_id':BOOT,'vsrv':status,
 'new_pulse_command_emitted':False,'native_close_stop':True,
 'camera':{k:health.get(k) for k in ['pid','detection_hz','identity_recognition','observation_age_ms','camera_error','detector_error']}}),flush=True)
