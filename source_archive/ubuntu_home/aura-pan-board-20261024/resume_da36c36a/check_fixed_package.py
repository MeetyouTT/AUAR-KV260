import json,sys
from pathlib import Path
P=Path('/home/root/aura-native-live-20261024/ops/be72669aa53de735/pan-face-edge-v5/fixed-motion-bench-v1')
sys.path.insert(0,str(P))
from board_fixed_cli import preflight
manifest,control=preflight('9a47a0319dc67644bf871497715da70171b39d329ec335b16b56079dc6850718')
sys.path.extend(['/home/root/aura-native-live-20261024/ops/be72669aa53de735/pan-face-edge-v5/continuous-v10r15',
 '/home/root/aura-pan-vsrv2-20261024/778d2512-1236ccf4-r2/driver'])
from register_model import Clock,Registers
from fixed_bench_adapter import FixedBenchDriver
from vsrv_driver import PhysicalReference
from run_fixed_motion import BenchPermit,plan_digest,run_fixed_motion
clock=Clock();registers=Registers(clock,1420)
driver=FixedBenchDriver(registers,0x778d2512,'fixture-current-boot',minimum_us=1415,maximum_us=1420,clock=clock,sleep=clock.sleep)
reference=PhysicalReference(driver.boot_id,1420,'fixture','fixture',1,True,True)
rows=next(x['samples'] for x in json.loads((P/'plans.json').read_text())['cases'] if x['direction_in_pulse_space']==-1)
permit=BenchPermit(driver.boot_id,'fixture','fixture',1420,1415,1420,1234,9.,14.,plan_digest(rows))
report=run_fixed_motion(driver,reference,permit,rows,clock=clock,sleep=clock.sleep)
assert report['stop_confirmed'] and len(report['commands'])==98 and registers.values[0x0c]==0
print(json.dumps({'status':'BOARD_CPU_REGISTER_MODEL_AND_PREFLIGHT_PASS','commands_in_model':98,
 'model_final_width':registers.values[0x2c],'model_stop_confirmed':True,'real_MMIO_opened':False,'real_motion_commands':0,
 'native_transport_imported':'batch_transport' in sys.modules,'package_sha256':'9a47a0319dc67644bf871497715da70171b39d329ec335b16b56079dc6850718'}))
