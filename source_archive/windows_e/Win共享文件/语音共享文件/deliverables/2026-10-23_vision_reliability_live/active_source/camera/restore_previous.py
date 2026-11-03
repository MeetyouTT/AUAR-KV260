import hashlib,json,sys
from pathlib import Path
sys.dont_write_bytecode=True
if sys.flags.optimize:raise RuntimeError('Assertions required')
root=Path('/home/root/aura-vision-reliability-20261023/f7624754038f3669')
for name,digest in {'handoff.py': 'af626c8f13f7586efbd7fe5841756af84799a215c7d4527363dffbd5ab95ec29', 'live_checks.py': 'b55f0ee0ab9e98b541864923f22c17814253ea22fad98a8de8dafeac7e67cd06'}.items():assert hashlib.sha256((root/name).read_bytes()).hexdigest()==digest
sys.path.insert(0,str(root))
from handoff import BoardOps
ops=BoardOps(Path('/home/root/aura-coordinated-switch-20261023/reliability-450136'));ops.verify()
args=sys.argv[1:];assert args in ([],['--check'],['--restore'],['--guard'])
if args in ([],['--check']):
 print(json.dumps({'passed':True,'read_only':True,'camera_pid':ops.pid('aura-camera-ui.service'),
  'unit_sha256':hashlib.sha256(ops.m.UNIT.read_bytes()).hexdigest(),
  'gui_override_present':Path(ops.meta['gui_override']).exists()}))
else:
 if args==['--restore']:
  ops.assert_idle_or_stopped();ops.assert_capture_closed()
  ops.meta['guard']='aura-reliability-manual-'+str(__import__('os').getpid());ops.save_meta();ops.arm()
 else:assert ops.meta['guard_armed']
 result=ops.restore();ops.disarm();print(json.dumps(result))
