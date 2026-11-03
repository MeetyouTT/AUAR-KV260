"""One focused lifetime edge using extracted original predicates, no /proc I/O."""
import ast
import hashlib
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
SOURCE=HERE.parent/'camera/normal_stop_current_owner.before_review.bin'
raw=SOURCE.read_bytes()
assert hashlib.sha256(raw).hexdigest()=='591b27912dad632f163886903568ad599661c2e22287ab8aa701d2035ab1271a'
tree=ast.parse(raw)
nodes=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in ('require','digest','owner')]
predicates=[]
for node in ast.walk(tree):
    if (isinstance(node,ast.Call) and isinstance(node.func,ast.Name) and node.func.id=='require' and node.args
            and isinstance(node.args[0],ast.Compare) and isinstance(node.args[0].ops[0],ast.NotEq)
            and isinstance(node.args[0].left,ast.Call) and isinstance(node.args[0].left.func,ast.Name)
            and node.args[0].left.func.id=='owner'):
        predicates.append(node.args[0])
assert len(predicates)==2
current={'exists':True,'birth':22,'command':b'original-camera-command'}
class ProcPath:
    def __init__(self,value):self.value=str(value)
    def __truediv__(self,key):return ProcPath(self.value+'/'+str(key))
    def exists(self):return current['exists']
    def read_text(self):
        fields=['0']*20;fields[0]='S';fields[19]=str(current['birth'])
        return '17 (public-test-process) '+' '.join(fields)
    def read_bytes(self):return current['command']
namespace={'Path':ProcPath,'hashlib':hashlib}
exec(compile(ast.Module(body=nodes,type_ignores=[]),'<actual-owner-helper>','exec'),namespace)
expected={'pid':17,'birth_ticks':'22','command_sha256':hashlib.sha256(b'original-camera-command').hexdigest()}
cases=[]
for label,exists,birth,command,expected_birth in (
    ('same_process_original_command',True,22,b'original-camera-command','22'),
    ('same_process_after_exec',True,22,b'another-executable-command','22'),
    ('same_process_integer_birth_input',True,22,b'original-camera-command',22),
    ('pid_reused_by_different_process',True,33,b'another-command','22'),
    ('process_absent',False,22,b'', '22')):
    current.update(exists=exists,birth=birth,command=command)
    wanted=dict(expected,birth_ticks=expected_birth)
    namespace.update(prior=wanted,expected={'camera_owner':wanted})
    old=[eval(compile(ast.Expression(body=predicate),'<actual-stopped-predicate>','eval'),namespace) for predicate in predicates]
    actual=namespace['owner'](wanted)
    lifetime_still_alive=actual is not None and int(actual['birth_ticks'])==int(wanted['birth_ticks'])
    cases.append({'case':label,'original_gui_and_camera_stopped_predicates_pass':old,
        'same_pid_birth_still_alive':lifetime_still_alive,
        'correct_stopped_result_by_lifetime':not lifetime_still_alive})
assert all(cases[1]['original_gui_and_camera_stopped_predicates_pass']) and cases[1]['same_pid_birth_still_alive']
assert all(cases[2]['original_gui_and_camera_stopped_predicates_pass']) and cases[2]['same_pid_birth_still_alive']
assert all(cases[3]['original_gui_and_camera_stopped_predicates_pass']) and not cases[3]['same_pid_birth_still_alive']
assert SOURCE.read_bytes()==raw
result={'status':'ORIGINAL_STOPPED_OWNER_PREDICATES_CAN_ACCEPT_LIVE_SAME_BIRTH_PROCESS',
    'source_sha256':hashlib.sha256(raw).hexdigest(),'cases':cases,
    'proposed_rule':'For death, absent PID or different birth only; for current active owner, keep full PID/birth/cmd pin equality.',
    'actual_proc_or_board_or_network_called':False,'source_modified':False}
(HERE/'NORMAL_STOP_OWNER_EDGE.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
print(json.dumps(result))
