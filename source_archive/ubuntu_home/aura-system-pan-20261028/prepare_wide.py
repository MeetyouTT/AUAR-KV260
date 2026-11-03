"""Prepare a new wide-capability platform without changing the paused draft."""
from pathlib import Path
import hashlib,json,shutil
R=Path('/home/ghmd/aura-pan-wide-20261028')
BASE=Path('/home/ghmd/aura-pan-joint-20261023')
DRAFT=Path('/home/ghmd/aura-pan-wide-1420-20261026')
R.mkdir(exist_ok=False)
shutil.copytree(BASE/'candidate',R/'candidate',ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
platform=R/'platform';platform.mkdir();(R/'implementation').mkdir()
for name in ['inputs','ip_cache']:
 if (DRAFT/'platform'/name).exists():shutil.copytree(DRAFT/'platform'/name,platform/name)
for name in ['repos.txt','pin.xdc','disabled_audio.sv']:shutil.copy2(DRAFT/'platform'/name,platform/name)
for name in ['prepare.tcl','implement.tcl']:shutil.copy2(DRAFT/name,R/name)
rtl=(DRAFT/'candidate/rtl/visual_servo.sv').read_text().replace('user-confirmed forward reference is 1420 us','500..2500 us capability; physical reference must be established separately').replace('CENTER_US = 1420','CENTER_US = 1500').replace("32'h14202602","32'h10282601")
(R/'candidate/rtl/visual_servo.sv').write_text(rtl);(platform/'visual_servo.sv').write_text(rtl)
p=R/'candidate/native/vsrv_protocol.h';p.write_text(p.read_text().replace('0x778d2512u','0x10282601u').replace('aura-visual-servo-b4096-v2.bit.bin','aura-visual-servo-b4096-wide-v1.bit.bin'))
p=R/'candidate/runtime/aura/board/motion/vsrv_driver.py';p.write_text(p.read_text().replace('0x778d2512','0x10282601').replace('MIN_LEASE_MS = 3','MIN_LEASE_MS = 4').replace('1400 <=','500 <=').replace('<= 1600','<= 2500'))
script=(DRAFT/'build_joint.py').read_text().replace('center-1420 wide-pulse','wide-pulse').replace("build_id='0x14202602', center_us=1420","build_id='0x10282601', center_us=1500").replace('str(0x14202602)','str(0x10282601)')
(R/'build_joint.py').write_text(script)
record={'status':'PREPARED_NOT_VALIDATED','build_id':'0x10282601','pulse_capability_us':[500,2500],'reset_register_us':1500,'mechanical_center_changed':False,'mechanical_angle_calibrated':False,'motion_commands':0,'board_deployed':False,'source_baseline':str(BASE),'previous_paused_draft_unchanged':True,'user_intent':'Cancel previous servo limits and check integrated operation; latest continue; retain lease/STOP and speed protection','files':{str(p.relative_to(R)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [R/'candidate/rtl/visual_servo.sv',platform/'visual_servo.sv',R/'candidate/native/vsrv_protocol.h',R/'build_joint.py']}}
(R/'PREPARATION.json').write_text(json.dumps(record,indent=2)+'\n');print(json.dumps(record))
