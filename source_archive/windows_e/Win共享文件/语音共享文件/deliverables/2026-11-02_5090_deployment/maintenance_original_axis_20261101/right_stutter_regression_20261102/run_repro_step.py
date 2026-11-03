import datetime,hashlib,importlib.util,json,os,sys
from pathlib import Path
B=Path('E:/Win共享文件/语音共享文件/deliverables/2026-11-02_5090_deployment');J=B/'joint_acceptance_180s_20261102';L=Path(__file__).parent;step=sys.argv[1];assert step in ['start','stop']
gpath=J/'AXIS_RIGHT_STUTTER_REPRO_PHASE_HANDOFF.json';g=json.loads(gpath.read_bytes())
if step=='start':
 assert g['permission_active'] and g['status']=='ACTIVE_AXIS_EXCLUSIVE_ORIGINAL_FOLLOW_20S_DIAGNOSTIC_REPRODUCTION'
 assert g['operator_thread']=='01a19b64-8194-70e3-806b-03fa9a283918'
 assert datetime.datetime.now(datetime.timezone.utc)<datetime.datetime.fromisoformat(g['may_begin_before_host_utc'])
source=(L/'repro_api_common.py').read_text(encoding='utf-8')+'\n'+(L/('repro_'+step+'.py')).read_text(encoding='utf-8');compile(source,'<original-API-repro-'+step+'>','exec')
def save_new(p,x):
 with p.open('x',encoding='utf-8',newline='\n') as f:json.dump(x,f,ensure_ascii=False,indent=2);f.write('\n');f.flush();os.fsync(f.fileno())
save_new(L/('REPRO_'+step.upper()+'_HOST_INTENT.json'),{'host_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'phase_sha256':hashlib.sha256(gpath.read_bytes()).hexdigest(),'step':step,'command':'pan_face_follow' if step=='start' else 'pan_stop','once':True,'source_sha256':hashlib.sha256(source.encode()).hexdigest()})
t=Path('E:/Win共享文件/语音共享文件/deliverables/2026-10-18_board_dialogue/board_ssh.py');assert hashlib.sha256(t.read_bytes()).hexdigest()=='6aefec94f620c6c86fa6b17c83613b22c8599e899cb2c2fcaf36c9cdd17c7373';spec=importlib.util.spec_from_file_location('axis_original_repro_strict',t);mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
try:
 raw=mod.ssh('python3 -B -',source,timeout=15)
 if isinstance(raw,bytes):raw=raw.decode()
 value=json.loads(raw);save_new(L/('REPRO_'+step.upper()+'.json'),value)
except BaseException as e:
 save_new(L/('REPRO_'+step.upper()+'_HOST_ERROR.json'),{'error_type':type(e).__name__,'error':str(e),'original_command_must_not_be_resent':True});raise
print(json.dumps({k:v for k,v in value.items() if k not in ['report_data','stop_snapshots']},ensure_ascii=True))
