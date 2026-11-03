"""Strict, one-shot transport for the separately granted metadata-only phase."""
import datetime,hashlib,importlib.util,json,os,sys
from pathlib import Path
B=Path('E:/Win共享文件/语音共享文件/deliverables/2026-11-02_5090_deployment');J=B/'joint_acceptance_180s_20261102';L=Path(__file__).parent
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
load=lambda p:json.loads(Path(p).read_bytes())
G=load(J/'AXIS_BINDING_REFRESH_PHASE_HANDOFF.json')
assert sha(J/'AXIS_BINDING_REFRESH_PHASE_HANDOFF.json')=='7b1f3f1de563a8488f0692e4f7fb29d559a9e82aa79d7016fed45f9aaf5e62dc'
assert G['permission_active'] and G['status']=='ACTIVE_AXIS_EXCLUSIVE_ORIGINAL_PAN_METADATA_BINDING'
assert G['operator_thread']=='01a19b64-8194-70e3-806b-03fa9a283918'
for key,name in [('CPU_camera_result_pin','CPU_CAMERA_RESTORE_RESULT.json'),('CPU_camera_explicit_return_pin','CPU_DEVICE_RETURNED_AFTER_CAMERA_RESTORE.json'),('wide_ID_STOP_result_pin','AXIS_WIDE_IDSTOP_RESULT.json')]:assert sha(J/name)==G[key]['sha256']
cpu=load(J/'CPU_CAMERA_RESTORE_RESULT.json');axis=load(J/'AXIS_WIDE_IDSTOP_RESULT.json')
C={'pins':cpu['component_sha256'],'selected_sources':cpu['selected_source_sha256'],'wide_root':axis['board_transaction_root'],'context':axis['context'],'IDSTOP_sha256':axis['identity_stop_report_sha256']}
step=sys.argv[1]
assert step in ['preflight','dryrun','apply','verify']
if step=='preflight':assert datetime.datetime.now(datetime.timezone.utc)<datetime.datetime.fromisoformat(G['may_begin_before_host_utc'])
else:assert (L/'preflight.json').is_file()
code=(L/(step+'.py')).read_text(encoding='utf-8')
source='import json\nG=json.loads('+repr(json.dumps(G))+')\nC=json.loads('+repr(json.dumps(C))+')\n'+code
compile(source,'<axis-original-binding-'+step+'>','exec')
def write_new(p,obj):
    with p.open('x',encoding='utf-8',newline='\n') as f:json.dump(obj,f,ensure_ascii=False,indent=2);f.write('\n');f.flush();os.fsync(f.fileno())
write_new(L/(step+'_HOST_INTENT.json'),{'host_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'grant_sha256':sha(J/'AXIS_BINDING_REFRESH_PHASE_HANDOFF.json'),'source_sha256':hashlib.sha256(source.encode()).hexdigest(),'step':step,'metadata_only':True})
t=Path('E:/Win共享文件/语音共享文件/deliverables/2026-10-18_board_dialogue/board_ssh.py');assert sha(t)=='6aefec94f620c6c86fa6b17c83613b22c8599e899cb2c2fcaf36c9cdd17c7373'
spec=importlib.util.spec_from_file_location('axis_metadata_strict_transport',t);mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
try:
    raw=mod.ssh('python3 -B -',source,timeout=55)
    if isinstance(raw,bytes):raw=raw.decode('utf-8')
    value=json.loads(raw);write_new(L/(step+'.json'),value)
except BaseException as e:
    write_new(L/(step+'_HOST_ERROR.json'),{'error_type':type(e).__name__,'error':str(e),'mutating_step_must_not_be_replayed':step=='apply'})
    raise
print(json.dumps({k:v for k,v in value.items() if k not in ['component_sha256','pins','selected_sources']},ensure_ascii=True,indent=2))
