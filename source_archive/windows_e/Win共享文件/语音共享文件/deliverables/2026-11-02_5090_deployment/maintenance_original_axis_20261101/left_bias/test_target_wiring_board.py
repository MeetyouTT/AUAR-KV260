"""Pure math and actual entry wiring; no actuator modules or devices."""
import argparse
import ast
import base64
import contextlib
import hashlib
import io
import json
from pathlib import Path
import sys
from types import SimpleNamespace

source=base64.b64decode('CANDIDATE_BASE64')
assert hashlib.sha256(source).hexdigest()=='9adb90c31efbf9c57d5e60f497c429bfcb3523be04ea6503d37552cfba3d4be9'
root=Path('/home/root/aura-pan-wide-20261028/control-10282601')
sys.path[:0]=[str(root),'/home/root/aura-board-business-20261030/production-5259eab11e42af13/runtime/aura']
assert hashlib.sha256((root/'continuous_face_control.py').read_bytes()).hexdigest()=='79bd5380068fbf3729144ec0b7ab9607e16e24d492081d59bcd0c85a98429b81'
from continuous_face_control import EdgeConfig,FaceEdgeController
tree=ast.parse(source);main=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='main')
setup=[]
for n in main.body:
    if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='a' for t in n.targets):break
    setup.append(n)
ns={'argparse':argparse,'Path':Path,'__doc__':'Pure parser test'}
exec(compile(ast.Module(body=setup,type_ignores=[]),'actual-entry-parser','exec'),ns)
parser=ns['p']
required=[]
for key in ('manifest','context','app-root','output','direction-evidence','human-evidence','zone-settings'):
    required+=['--'+key,'unused-pure-test']
required+=['--manifest-sha256','unused','--confirmation','FACE_ZONE_CONTINUOUS']
call=next(n for n in ast.walk(main) if isinstance(n,ast.Call) and isinstance(n.func,ast.Name) and n.func.id=='EdgeConfig')
expression=compile(ast.Expression(call),'actual-entry-config','eval')
zone={'left_ratio':.1,'right_ratio':.8064720153808593}
def config(args):return eval(expression,{'EdgeConfig':EdgeConfig,'zone':zone,'a':args})
results={}
default=parser.parse_args(required)
assert default.target_center_ratio==.5 and config(default).target_center_ratio==.5
results['old_invocation_keeps_original_center']=True
args=parser.parse_args(required+['--target-center-ratio','0.45']);cfg=config(args)
assert cfg.target_center_ratio==.45 and cfg.center_tolerance_ratio==.03
results['actual_cli_wires_left_biased_target']=True
for label,points in [('left',[(.10,True,False),(.30,False,True),(.43,False,True)]),
                     ('right',[(.90,False,False),(.50,False,True),(.47,False,True)])]:
    control=FaceEdgeController('pure-test-boot',1500,config=cfg,polarity=1)
    for i,(center,left_outside,inside) in enumerate(points):
        control.recenter_decision(center,left_outside,inside)
        if i<len(points)-1:assert control.recenter_active and control.reason!='SAFE_ZONE_HOLD'
    assert not control.recenter_active and control.recenter_completed and control.reason=='SAFE_ZONE_HOLD'
    results[label+'_crossing_stops_in_band_left_of_white_line']=True
invalid=(float('nan'),float('inf'),float('-inf'),0.,1.,.1,.81)
for value in invalid:
    bad=SimpleNamespace(target_center_ratio=value)
    try:config(bad)
    except ValueError:pass
    else:raise AssertionError('Invalid stop target accepted')
results['invalid_and_outside_band_targets_rejected']=True
with contextlib.redirect_stderr(io.StringIO()):
    try:parser.parse_args(required+['--target-center-ratio','left'])
    except SystemExit as e:assert e.code==2
    else:raise AssertionError('Nonnumeric target accepted')
results['nonnumeric_cli_rejected']=True
assert not any(name in sys.modules for name in ('vsrv_driver','vsrv_transport','deadline_driver','hardware_slew_session'))
print(json.dumps({'status':'PASS','checks':results,'invalid_cases':len(invalid),
    'candidate_sha256':hashlib.sha256(source).hexdigest(),'actuator_imported':False,'device_opened':False,'board_writes':False}))
