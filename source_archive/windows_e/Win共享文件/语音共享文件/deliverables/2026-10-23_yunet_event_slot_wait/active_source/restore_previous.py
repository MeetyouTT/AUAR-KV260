import hashlib,json,os,subprocess,sys
from pathlib import Path
sys.dont_write_bytecode=True
if sys.flags.optimize:raise RuntimeError('Assertions required')
root=Path('/home/root/aura-slot-wait-release-20261023/4970321c51bdea6c');assert root.resolve()==root
for name,digest in {'handoff.py': 'f43ddd90fa5ef379f2802b08d02b373f8417c63c1ce0fc4ef80cb2f8237ea807', 'live_checks.py': 'c095d94c2b7e956948fb1324b78dea3717971a924be598a4fd553a2d4e52a965'}.items():assert hashlib.sha256((root/name).read_bytes()).hexdigest()==digest
sys.path.insert(0,str(root))
from handoff import BoardOps
ops=BoardOps(Path('/home/root/aura-coordinated-switch-20261023/slot-wait-298300'));ops.verify()
args=sys.argv[1:];assert args in ([],['--check'],['--restore'],['--guard'])
if args==['--guard']:
 assert ops.meta['guard_armed']
 print(json.dumps(ops.restore()))
elif args==['--restore']:
 ops.assert_idle_or_stopped()
 timer='aura-bounded-manual-restore-'+str(os.getpid())
 ops.meta['guard']=timer;ops.save_meta()
 ops.m.command(['systemd-run','--unit='+timer,'--on-active=450s','--property=RuntimeMaxSec=300',
                '/usr/bin/python3','-B',__file__,'--guard'],timeout=10)
 ops.meta['guard_armed']=True;ops.save_meta();ops.assert_guard_armed()
 result=ops.restore();ops.disarm();print(json.dumps(result))
else:
 print(json.dumps({'passed':True,'read_only':True,'camera_pid':ops.pid('aura-camera-ui.service'),
                  'current_unit_sha256':hashlib.sha256(ops.m.UNIT.read_bytes()).hexdigest(),
                  'previous_unit_sha256':ops.meta['unit_hashes']['original']}))
