import hashlib,json,os,subprocess,sys
from pathlib import Path
sys.dont_write_bytecode=True
if sys.flags.optimize:raise RuntimeError('Assertions required')
root=Path('/home/root/aura-sface-formal-20261023/00b792619ce222d2');assert root.resolve()==root
for name,digest in {'handoff.py': 'f063cfcd743c1b94ecc73d39849cabeb18d077b5c9f7da771b263d50a43d51cd', 'live_checks.py': '29fe240c905db5c8cbd6a23e42b2e1b48fae85c411e20b0f684f08afc734775b'}.items():assert hashlib.sha256((root/name).read_bytes()).hexdigest()==digest
sys.path.insert(0,str(root))
from handoff import BoardOps
ops=BoardOps(Path('/home/root/aura-coordinated-switch-20261023/sface-formal-333217'));ops.verify()
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
