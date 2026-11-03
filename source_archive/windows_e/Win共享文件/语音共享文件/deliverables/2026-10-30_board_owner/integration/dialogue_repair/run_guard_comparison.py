"""Compare source-only guard variants on fresh synthetic ARM databases."""
import argparse
import ast
import base64
import hashlib
import json
from pathlib import Path
import sys

HERE=Path(__file__).resolve().parent
PROJECT=HERE.parents[3]
sys.path.insert(0,str(PROJECT/'deliverables/2026-10-18_board_dialogue'))
from board_ssh import ssh

REMOTE=r'''
import base64,hashlib,http.client,json,pathlib,sys,tempfile,types
root=pathlib.Path('/home/root/aura-board-business-20261030/production-5259eab11e42af13/runtime/aura')
startup=(root.parent.parent/'startup/config.json').read_bytes()
assert hashlib.sha256(startup).hexdigest()==SPEC['startup_sha256']
assert pathlib.Path('/proc/sys/kernel/random/boot_id').read_text().strip()==SPEC['boot_id']
pins=json.loads(startup)['component_sha256']
for rel in ('common/board_memory.py','common/memory_commands.py','common/board_timeline_clock.py'):
 assert hashlib.sha256((root/rel).read_bytes()).hexdigest()==pins[rel]
assert pins['common/board_memory.py']==OLD_PIN
sys.path.insert(0,str(root))
import common
probe=types.ModuleType('public_guard_probe')
exec(compile(base64.b64decode(PROBE),'public_guard_probe.py','exec'),probe.__dict__)
modules={}
for label,raw in [('baseline',(root/'common/board_memory.py').read_bytes()),('candidate',base64.b64decode(CANDIDATE))]:
 expected=OLD_PIN if label=='baseline' else NEW_PIN
 assert hashlib.sha256(raw).hexdigest()==expected
 name='common.public_guard_comparison_'+label
 module=types.ModuleType(name);module.__package__='common';sys.modules[name]=module
 exec(compile(raw,name+'.py','exec'),module.__dict__);modules[label]=module
rows=[]
for dependencies,iterations in [(8,60),(32,40)]:
 for index,label in enumerate(('baseline','candidate','candidate','baseline')):
  with tempfile.TemporaryDirectory(prefix='aura-public-guard-comparison-') as temporary:
   directory=pathlib.Path(temporary)
   value=probe.one_case(modules[label],directory,dependencies,iterations)
  assert not directory.exists()
  rows.append(dict(order=index,variant=label,**value))
out=dict(status='SYNTHETIC_ARM_GUARD_COMPARISON_COMPLETE',startup_sha256=SPEC['startup_sha256'],
 before_sha256=OLD_PIN,after_sha256=NEW_PIN,rows=rows,private_database_accessed=False,
 private_data_replayed=False,model_or_device_used=False,temporary_directories_cleaned=True,
 source_installed=False,claim='synthetic_microbenchmark_not_actual_playback_acceptance')
print(json.dumps(out))
'''

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('candidate',type=Path);args=parser.parse_args()
    raw=args.candidate.read_bytes();ast.parse(raw,feature_version=(3,9))
    spec=json.loads((HERE.parent/'production_business_acceptance/spec.json').read_text(encoding='utf-8'))
    old_pin=hashlib.sha256((HERE/'before/common/board_memory.py').read_bytes()).hexdigest()
    probe=(HERE/'memory_guard_probe/probe_prepared_guard.py').read_bytes()
    assert hashlib.sha256(probe).hexdigest()=='86e5de6a47b9a7cab904e0549673d73084472e3ccde1068219c77e0d7e70fd3c'
    new_pin=hashlib.sha256(raw).hexdigest()
    values=dict(SPEC=spec,OLD_PIN=old_pin,NEW_PIN=new_pin,
        PROBE=base64.b64encode(probe).decode(),CANDIDATE=base64.b64encode(raw).decode())
    script='\n'.join(key+'='+repr(value) for key,value in values.items())+'\n'+REMOTE
    result=json.loads(ssh('python3 -B -',script,timeout=100))
    output=HERE/'guard_candidate'/('actual_arm_comparison_'+new_pin[:16]+'.json')
    output.parent.mkdir(exist_ok=True);output.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(result))
