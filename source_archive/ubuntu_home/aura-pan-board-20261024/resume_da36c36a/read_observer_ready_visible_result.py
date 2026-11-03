import json,sys
from pathlib import Path
P=Path('/home/root/aura-native-live-20261024/ops/be72669aa53de735/pan-face-edge-v5/fixed-motion-visible-v2');sys.path.insert(0,str(P))
from board_fixed_cli import preflight,R,OLD,BOOT,OPS
manifest,control=preflight('6b9cddcfeb78cd49708a01b9f99e5b20f894448818849376556a6a596bc09b83')
ref=json.loads((R/'attended-fixed-reference.json').read_text());trial=R/('fixed-trajectory-'+ref['authorization_id']+'.json')
report=json.loads(trial.read_text());C=OPS/'pan-face-edge-v5/continuous-v10r15'
sys.path.extend([str(C),str(OLD/'driver')])
from batch_transport import BatchRegisters
from batch_driver import BatchDriver
lib=C/'libvsrv_batch.so';pin=next(x['sha256'] for x in control['files'] if x['destination']==str(lib))
with BatchRegisters(lib,pin,BOOT,manifest['runtime_files']) as io:
 d=BatchDriver(io,0x778d2512,BOOT);before=d.status();stopped=d.stop()
 assert stopped['flags']==0 and stopped['lease_left_ms']==0
print(json.dumps({'report_path':str(trial),'report':report,'fresh_before_stop':before,'fresh_stopped':stopped,
 'additional_ARM':0,'additional_COMMIT':0,'STOP_verified':True}))
