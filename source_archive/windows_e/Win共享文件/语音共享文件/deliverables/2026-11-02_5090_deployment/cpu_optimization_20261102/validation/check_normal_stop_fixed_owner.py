"""Targeted actual-owner helper check and source-boundary audit, local only."""
import ast
import hashlib
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
SOURCE=HERE.parent/'camera/normal_stop_current_owner.py'
raw=SOURCE.read_bytes()
assert hashlib.sha256(raw).hexdigest()=='4a5e374eacc825e16a22664dc6ef1137f5e0950be3dc8b3e477f791faf5e2e91'
tree=ast.parse(raw);functions={n.name:n for n in tree.body if isinstance(n,ast.FunctionDef)}
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
exec(compile(ast.Module(body=[functions[n] for n in ('require','digest','owner','same_lifetime')],type_ignores=[]),'<actual-fixed-owner-functions>','exec'),namespace)
expected={'pid':17,'birth_ticks':'22','command_sha256':hashlib.sha256(b'original-camera-command').hexdigest()}
cases=[]
for label,exists,birth,command in (
    ('same_process_original_command',True,22,b'original-camera-command'),
    ('same_process_after_exec',True,22,b'another-executable-command'),
    ('pid_reused_by_different_process',True,33,b'another-command'),
    ('process_absent',False,22,b'')):
    current.update(exists=exists,birth=birth,command=command)
    alive=namespace['same_lifetime'](expected)
    matches=namespace['owner'](expected)==expected
    assert alive==(exists and birth==22)
    cases.append({'case':label,'same_lifetime':alive,'current_full_command_pin_matches':matches})
try:namespace['same_lifetime'](dict(expected,birth_ticks=22))
except RuntimeError:bad_birth_rejected=True
else:raise RuntimeError('Noncanonical birth input was accepted')
main=functions['main']
dry=next(n for n in main.body if isinstance(n,ast.If) and isinstance(n.test,ast.UnaryOp) and isinstance(n.test.op,ast.Not) and isinstance(n.test.operand,ast.Attribute) and n.test.operand.attr=='stop')
assert isinstance(dry.body[-1],ast.Return)
dry_index=main.body.index(dry)
assert not any(isinstance(n,ast.Call) and ((isinstance(n.func,ast.Name) and n.func.id=='create') or (isinstance(n.func,ast.Attribute) and n.func.attr in ('mkdir','write_text','write_bytes'))) for stmt in main.body[:dry_index+1] for n in ast.walk(stmt))
stop_calls=[]
for n in ast.walk(tree):
    if isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute) and isinstance(n.func.value,ast.Name) and n.func.value.id=='subprocess' and n.func.attr=='run' and n.args and isinstance(n.args[0],ast.List):
        argv=[item.value if isinstance(item,ast.Constant) else None for item in n.args[0].elts]
        if argv[:2]==['systemctl','stop']:stop_calls.append(argv)
assert stop_calls==[['systemctl','stop','--no-block','aura-camera-ui.service']]
forbidden={'kill','terminate','send_signal','killpg','system','Popen'}
assert not any(isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute) and n.func.attr in forbidden for n in ast.walk(tree))
closure=ast.get_source_segment(raw.decode(),functions['source_closure'])
assert all(value in closure for value in ('source_closure','selected_readback','owner_run_config','native_python_manifest','native_operator_manifest','native_c_unit_manifest','native_library','camera_systemd','FragmentPath','DropInPaths'))
assert 'len(manifest[\'files\'])==222' in closure and 'len(operator[\'files\'])==7' in closure and 'len(unit_manifest[\'files\'])==6' in closure
assert "b77c32b3863b9464006ac1bb7f16c8f767113925d9142d77e4755f1ce365527e" in closure
assert "no_service_processes('aura-avatar-ui.service')" in raw.decode() and "no_service_processes('aura-camera-ui.service')" in raw.decode()
assert SOURCE.read_bytes()==raw
result={'status':'PASS_FIXED_OWNER_MODEL_AND_STATIC_STOP_BOUNDARIES',
    'source_sha256':hashlib.sha256(raw).hexdigest(),'owner_cases':cases,
    'noncanonical_integer_birth_rejected_before_proc_use':bad_birth_rejected,
    'dry_run_returns_before_any_directory_or_evidence_write':True,
    'only_one_original_no_block_stop_call':True,'camera_force_kill_or_retry_present':False,
    'new_closure_members_and_original_readback_method_present':True,
    'gui_and_poststop_camera_cgroup_checks_present':True,
    'actual_source_closure_or_systemd_or_proc_queried':False,
    'actual_linux_dry_run_executed':False,'source_modified':False}
(HERE/'NORMAL_STOP_FIXED_OWNER_CHECK.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
print(json.dumps(result))
