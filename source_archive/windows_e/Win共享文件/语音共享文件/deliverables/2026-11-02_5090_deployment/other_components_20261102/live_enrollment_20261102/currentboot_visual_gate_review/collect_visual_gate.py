"""Few read-only GETs with RAM-only projection; no business/private data exports."""
import datetime
import hashlib
import importlib.util
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE.parents[2]
HELPER = OUT.parent / '2026-10-18_board_dialogue/board_ssh.py'
assert hashlib.sha256(HELPER.read_bytes()).hexdigest() == '6aefec94f620c6c86fa6b17c83613b22c8599e899cb2c2fcaf36c9cdd17c7373'
spec = importlib.util.spec_from_file_location('strict_readonly_transport', HELPER)
transport = importlib.util.module_from_spec(spec)
spec.loader.exec_module(transport)
remote = r'''
import ast,copy,hashlib,http.client,json,math,time
from pathlib import Path
root=Path('/home/root/aura-board-business-20261030/production-5259eab11e42af13')
sr=(root/'startup/config.json').read_bytes(); startup=json.loads(sr)
aura=Path(startup['runtime'])/'aura'
boot=Path('/proc/sys/kernel/random/boot_id').read_text().strip()
ui=json.loads((aura/'config/board_avatar_gtk.json').read_bytes())
spec=ui['board_business']['face_readback']; br=Path(spec['path']).read_bytes(); binding=json.loads(br)
proc=Path('/proc')/str(binding['camera_pid'])
try:
 actual_cmd_sha=hashlib.sha256((proc/'cmdline').read_bytes()).hexdigest()
 actual_birth=(proc/'stat').read_text().rsplit(')',1)[1].split()[19]
 owner_running=True
except (OSError,ValueError,IndexError):
 actual_cmd_sha=actual_birth=None;owner_running=False
run=json.loads(Path(binding['camera_config']).read_bytes())
identity_config=json.loads(Path(binding['identity_config']).read_bytes())
checks={}
for name,expected in {
 'board/identity/voice_enrollment.py':'a9113ba40efc49828ee158554b2dae70485858396680918458f6f96bba16bacb',
 'board/interaction/ui_services.py':'b55ee295e2cb5494f387fbaa4aa081fd1d6bffd57588c018c5f31daae56bd711',
 'board/runtime/board_business.py':'b08209eca7979825e26845080bca5e1d64e065d3cabd1178df763a93540573f2'}.items():
 actual=hashlib.sha256((aura/name).read_bytes()).hexdigest()
 checks[name]={'matches_expected':actual==expected,'matches_startup_pin':actual==startup['component_sha256'].get(name)}
contract_path=aura/'board/interaction/ui_contract.py';contract_raw=contract_path.read_bytes()
checks['board/interaction/ui_contract.py']={'matches_startup_pin':hashlib.sha256(contract_raw).hexdigest()==startup['component_sha256'].get('board/interaction/ui_contract.py')}
tree=ast.parse(contract_raw.decode('utf-8')); ns={'copy':copy,'math':math}
for n in tree.body:
 if isinstance(n,ast.Assign) and len(n.targets)==1 and isinstance(n.targets[0],ast.Name) and n.targets[0].id in ('PROTOCOL','MODULE_STATES','ACTIONS'):
  ns[n.targets[0].id]=ast.literal_eval(n.value)
funcs=[copy.deepcopy(n) for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in ('integer','text','require','target_key','validate_snapshot')]
exec(compile(ast.Module(body=funcs,type_ignores=[]),'<original-visual-metadata-validator>','exec'),ns)
def get(port,path):
 c=http.client.HTTPConnection('127.0.0.1',port,timeout=3)
 try:
  c.request('GET',path);r=c.getresponse();raw=r.read(2097153)
  if r.status!=200 or len(raw)>2097152:raise ValueError('FIXED_HTTP_READ_REJECTED')
  return json.loads(raw)
 finally:c.close()
def fixed(v,allowed):return v if v in allowed else 'UNAVAILABLE'
def projection(value):
 if not isinstance(value,dict):return None
 selected={k:value.get(k) for k in ('protocol_version','board_boot_id','service_epoch','sequence','observed_mono_ms','ttl_ms','source_kind','context')}
 modules=value.get('modules') or {};identity=modules.get('identity') or {};target=modules.get('target') or {}
 kept={}
 for name,keys in {'camera':('state','preview_transport'),'vision':('state','people_count')}.items():
  original=modules.get(name) or {};kept[name]={k:original[k] for k in keys if k in original}
 kept['target']={k:target[k] for k in ('state','selected') if k in target}
 kept['target']['tracks']=[{'key':r.get('key'),'label':'face'} for r in target.get('tracks',[]) if isinstance(r,dict)]
 face={k:identity[k] for k in ('state','db_version','target_kind','face_count','face_target','face_preview','face_attention') if k in identity}
 if 'face_targets' in identity:face['face_targets']=[{'key':r.get('key'),'label':'face'} for r in identity['face_targets'] if isinstance(r,dict)]
 sampling=identity.get('enrollment_sampling')
 if isinstance(sampling,dict):
  face['enrollment_sampling']={k:sampling.get(k) for k in ('session_id','stage','counts','total','total_required','bound_target') if k in sampling}
  face['enrollment_sampling']['detail']=''
 face['people']=[]
 kept['identity']=face;selected['modules']=kept
 selected['capabilities']={k:v for k,v in value.get('capabilities',{}).items() if k in ('identity_enroll','identity_sample_start','identity_sample_cancel')}
 if 'preview' in value:selected['preview']=value['preview']
 return selected
def summarize(value):
 now=round(time.monotonic()*1000)
 if not isinstance(value,dict):return {'present':False}
 p=projection(value);m=p['modules'];i=m['identity'];t=m['target'];caps=p['capabilities'];ctx=p['context'] or {}
 target=i.get('face_target') if i.get('target_kind')=='face' else t.get('selected')
 count=i.get('face_count') if i.get('target_kind')=='face' else m['vision'].get('people_count')
 sampling=i.get('enrollment_sampling') or {};ref=i.get('face_preview');attention=i.get('face_attention')
 valid=False
 try:ns['validate_snapshot'](p,boot,now);valid=True
 except (ValueError,KeyError,TypeError):pass
 fresh=type(p.get('observed_mono_ms')) is int and type(p.get('ttl_ms')) is int and p['observed_mono_ms']<=now+100 and now<p['observed_mono_ms']+p['ttl_ms']
 face_ref_fresh=bool(ref and type(ref.get('captured_mono_ms')) is int and type(ref.get('ttl_ms')) is int and -100<=now-ref['captured_mono_ms']<ref['ttl_ms'])
 source_actual=p.get('source_kind')=='actual';boot_current=p.get('board_boot_id')==boot
 capabilities_ok=bool(caps.get('identity_enroll') or sampling and caps.get('identity_sample_start'))
 return {'present':True,'allowed_visual_projection_passes_original_validator':valid,
  'boot_is_current':boot_current,'source_kind':fixed(p.get('source_kind'),('actual','fixture')),
  'service_epoch_nonempty':isinstance(p.get('service_epoch'),str) and bool(p['service_epoch']),
  'context_shape_valid':set(ctx)=={'session_id','request_id','generation'},
  'context_session_nonempty':isinstance(ctx.get('session_id'),str) and bool(ctx['session_id']),
  'context_request_empty':ctx.get('request_id')=='','context_generation_nonnegative':type(ctx.get('generation')) is int and ctx['generation']>=0,
  'fresh':fresh,'age_ms':now-p['observed_mono_ms'] if type(p.get('observed_mono_ms')) is int else None,
  'ttl_ms':p.get('ttl_ms'),'camera_state':fixed(m['camera'].get('state'),('READY','LOST','ERROR','UNKNOWN')),
  'vision_state':fixed(m['vision'].get('state'),('READY','DEGRADED','ERROR','UNKNOWN')),
  'target_mode':fixed(i.get('target_kind'),('face',)),'face_count':i.get('face_count'),
  'people_count':m['vision'].get('people_count'),'single_target':count==1,'selected_target_present':bool(target),
  'selected_target_in_face_targets':bool(target and target in [row.get('key') for row in i.get('face_targets',[])]),
  'identity_state':fixed(i.get('state'),('UNKNOWN','KNOWN','ENROLLING','DELETED','ERROR')),
  'identity_database_revision':i.get('db_version'),'face_preview_present':bool(ref),'face_preview_fresh':face_ref_fresh,
  'face_preview_target_matches_selected':bool(ref and ref.get('target')==target),
  'frontal':attention.get('frontal') if isinstance(attention,dict) and type(attention.get('frontal')) is bool else None,
  'sampling_stage':fixed(sampling.get('stage'),('idle','collect','front','left','right','validate','ready','failed')),
  'sampling_counts':{k:v for k,v in (sampling.get('counts') or {}).items() if k in ('collect','front','left','right','validate') and type(v) is int},
  'sampling_total':sampling.get('total'),'identity_sample_start_capability':caps.get('identity_sample_start') is True,
  'identity_enroll_capability':caps.get('identity_enroll') is True,
  'camera_current_single_unknown_entry_gates_pass':bool(valid and fresh and source_actual and boot_current and count==1 and target and i.get('state')=='UNKNOWN' and capabilities_ok),
  'public_view_has_ui_cancelled_marker':'ui_cancelled' in value}
def owner(value):
 if not isinstance(value,dict):return None
 p=projection(value);i=p['modules']['identity']
 target=i.get('face_target') if i.get('target_kind')=='face' else p['modules']['target'].get('selected')
 return (p['board_boot_id'],p['service_epoch'],target,i.get('db_version'))
first=get(8790,'/v1/ui/status');first_summary=summarize(first)
gui=get(8783,'/api/state');runtime=gui.get('ui_runtime') or {};cached=runtime.get('snapshot')
gui_summary=summarize(cached)
flow=((gui.get('board_business') or {}).get('dialogue') or {}).get('voice_enrollment') or {}
time.sleep(.65)
second=get(8790,'/v1/ui/status');second_summary=summarize(second)
print(json.dumps({'current_boot_equals_expected_reboot':boot=='a6d4a069-e9b0-4065-8df7-dc23556b168e',
 'startup_stable_during_read':(root/'startup/config.json').read_bytes()==sr,
 'selected_binding_sha_matches_gui_pin':hashlib.sha256(br).hexdigest()==spec['sha256'],
 'selected_binding_boot_current':binding.get('board_boot_id')==boot,'selected_camera_process_running':owner_running,
 'selected_camera_birth_matches_process':actual_birth==binding.get('camera_start_ticks'),
 'selected_camera_cmdline_matches_process':actual_cmd_sha==binding.get('camera_cmdline_sha256'),
 'camera_run_identity_matches_selected_binding':run.get('identity')=={'enabled':True,'config':binding['identity_config']},
 'identity_schema_expected':identity_config.get('schema_version')=='aura-camera-identity-1',
 'identity_backend_kind_expected':identity_config.get('feature_backend',{}).get('kind')=='dpu_sface',
 'identity_ttl_matches_selected_binding':identity_config.get('result_ttl_ms')==binding.get('result_ttl_ms'),
 'public_source_pin_checks':checks,'camera_samples':[first_summary,second_summary],
 'camera_sequence_increased':second.get('sequence',0)>first.get('sequence',0),
 'camera_context_stable_between_samples':first.get('context')==second.get('context'),
 'camera_owner_stable_between_samples':owner(first)==owner(second),
 'gui_cache':gui_summary,'gui_service_link':fixed(runtime.get('link'),('READY','DISABLED','CONNECTING','ERROR','STALE','OFFLINE')),
 'gui_service_error_present':bool(runtime.get('error')),
 'gui_cache_context_matches_first_camera':isinstance(cached,dict) and cached.get('context')==first.get('context'),
 'gui_cache_owner_matches_first_camera':owner(cached)==owner(first),
 'gui_cache_owner_matches_second_camera':owner(cached)==owner(second),
 'gui_face_flow_stage':fixed(flow.get('stage'),('idle','name','authorize','sampling','confirm')),
 'gui_face_flow_active':flow.get('active') is True,
 'private_database_photos_audio_transcripts_names_personids_axis_or_service_commands_accessed':False,
 'get_count':3,'camera_status_get_count':2,'gui_state_get_count':1}))
'''
result = json.loads(transport.ssh('python3 -B -', remote, timeout=25))
output = {'host_observed_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(), **result}
(HERE / 'VISUAL_ENTRY_PRECONDITIONS.json').write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps(output, ensure_ascii=False))
