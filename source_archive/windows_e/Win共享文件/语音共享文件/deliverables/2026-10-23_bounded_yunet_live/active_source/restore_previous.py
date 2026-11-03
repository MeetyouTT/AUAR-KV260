import hashlib,json,os,subprocess,sys
from pathlib import Path
sys.dont_write_bytecode=True
if sys.flags.optimize:raise RuntimeError('Assertions required')
root=Path('/home/root/aura-bounded-release-20261023/64daead0d60439fd');assert root.resolve()==root
for name,digest in {'handoff.py': 'de8b83b8cb5b640a39e888eaee61b41163614cc2aabc4696f73da47dc52b4b6c', 'live_checks.py': 'a95877b5369aef49c9e6ea53a219715c1fb4d4c89071ff7e065cf4818b332f2b'}.items():assert hashlib.sha256((root/name).read_bytes()).hexdigest()==digest
sys.path.insert(0,str(root))
from handoff import BoardOps
ops=BoardOps(Path('/home/root/aura-coordinated-switch-20261023/bounded-251478'));ops.verify()
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
