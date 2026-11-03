import json,sys
from pathlib import Path
P=Path('/home/root/aura-native-live-20261024/ops/be72669aa53de735/pan-face-edge-v5/fixed-motion-visible-v2');sys.path.insert(0,str(P))
from board_fixed_cli import preflight,R,OLD,BOOT,OPS
manifest,control=preflight('6b9cddcfeb78cd49708a01b9f99e5b20f894448818849376556a6a596bc09b83')
C=OPS/'pan-face-edge-v5/continuous-v10r15';sys.path.extend([str(C),str(OLD/'driver')])
from register_model import Clock,Registers
from fixed_bench_adapter import FixedBenchDriver
from vsrv_driver import PhysicalReference
from run_fixed_motion import BenchPermit,plan_digest,run_fixed_motion
clock=Clock();registers=Registers(clock,1420)
driver=FixedBenchDriver(registers,0x778d2512,'fixture-current-boot',minimum_us=1402,maximum_us=1420,clock=clock,sleep=clock.sleep)
reference=PhysicalReference(driver.boot_id,1420,'fixture','fixture',1,True,True)
rows=json.loads((P/'plans.json').read_text())['samples']
permit=BenchPermit(driver.boot_id,'fixture','fixture',1420,1402,1420,1234,9.,20.,plan_digest(rows))
model=run_fixed_motion(driver,reference,permit,rows,clock=clock,sleep=clock.sleep)
assert model['stop_confirmed'] and model['stopped_readback']['width_us']==1420
from batch_transport import BatchRegisters
from batch_driver import BatchDriver
lib=C/'libvsrv_batch.so';pin=next(x['sha256'] for x in control['files'] if x['destination']==str(lib))
with BatchRegisters(lib,pin,BOOT,manifest['runtime_files']) as io:
 real=BatchDriver(io,0x778d2512,BOOT);before=real.status();stopped=real.stop()
 assert stopped['flags']==0 and stopped['lease_left_ms']==0 and stopped['width_us']==1420
s=json.loads((R/'state.json').read_text());s.update(phase='FIXED_TESTS_STOPPED_VISIBLE_R2_AWAITING_OBSERVER',current_last_command_us=1420,
 current_stopped_readback=stopped,fixed_visible_r2_root=str(P),fixed_visible_r2_manifest_sha256='6b9cddcfeb78cd49708a01b9f99e5b20f894448818849376556a6a596bc09b83',
 automatic_following=False,physical_fixed_smoothness_verified=False)
(R/'state.json').write_text(json.dumps(s,indent=2)+'\n')
print(json.dumps({'status':s['phase'],'boot_id':BOOT,'package_root':str(P),'model_commands':len(model['commands']),
 'model_final_width':model['stopped_readback']['width_us'],'fresh_stopped':stopped,
 'physical_visible_r2_executed':False,'real_ARM':0,'real_COMMIT':0,'real_STOP_verified':True,
 'original_r15_modified':False,'physical_smoothness_verified':False}))
