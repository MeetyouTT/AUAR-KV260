"""Dynamic vision/identity metadata projection; no service, device, database or motor access."""
import ast
import copy
import datetime
import hashlib
import http.client
import json
import math
from pathlib import Path
import subprocess
import time

BUSINESS = Path('/home/root/aura-board-business-20261030/production-5259eab11e42af13')
EXPECTED_QUERY_FIX = '85e415d00daa770d4d94ae58006a23ed9700067651a0448de80c99eb33ed1809'
IDENTITY_STATES = {'UNKNOWN','KNOWN','ENROLLING','DELETED','ERROR'}
REASONS = {'WAITING_FRAME','SERVICE_ERROR','MODEL_LOADING','MULTIPLE_FACES','TARGET_UNCONFIRMED',
    'NO_FACE_OR_TARGET','STALE_OR_FOREIGN_RESULT','MATCHED','AMBIGUOUS','EMPTY_GALLERY',
    'LOW_SIMILARITY','FEATURE_OR_QUALITY_UNAVAILABLE'}

def raw(path):
    path=Path(path)
    assert path.is_absolute() and path.resolve()==path and not path.is_symlink()
    assert path.suffix.lower() not in ('.db','.sqlite','.sqlite3') and path.stat().st_size < 64000000
    # This task explicitly excludes original motor configuration and control files.
    assert not str(path).startswith('/home/root/aura-pan-wide-')
    return path.read_bytes()

def digest(path):return hashlib.sha256(raw(path)).hexdigest()
def doc(path):return json.loads(raw(path))
def obj(value,key):return value.get(key,{}) if isinstance(value,dict) and isinstance(value.get(key),dict) else {}
def enum(value,allowed):return value if isinstance(value,str) and value in allowed else None
def numbers(value,keys):return {key:value[key] for key in keys if key in value and type(value[key]) in (int,float,bool)} if isinstance(value,dict) else {}

def unit(name):
    result=subprocess.run(['systemctl','show',name,'--property=MainPID,ActiveState,SubState,Job,Result,ExecMainStartTimestampMonotonic'],capture_output=True,text=True,timeout=4)
    assert result.returncode==0
    return dict(line.split('=',1) for line in result.stdout.splitlines() if '=' in line)

def owner(pid):
    proc=Path('/proc')/str(pid)
    return {'pid':pid,'birth_ticks':int((proc/'stat').read_text().rsplit(')',1)[1].split()[19]),
        'command_sha256':hashlib.sha256((proc/'cmdline').read_bytes()).hexdigest()}

def request(port,path):
    conn=http.client.HTTPConnection('127.0.0.1',port,timeout=3)
    try:
        conn.request('GET',path);response=conn.getresponse();body=response.read(2097153)
        assert response.status==200 and len(body)<=2097152
        value=json.loads(body);assert isinstance(value,dict)
        return value
    finally:conn.close()

def safe_result(value):
    if not isinstance(value,dict):return {}
    output=numbers(value,('ready','known','confirmed','calibrated','speaker_calibrated','speaker_known',
        'binding_active','name_waiting','automatic_profile_access','profile_access','authorized',
        'grant_active','grant_valid','candidate','pending','active','queued_or_active','fresh',
        'age_ms','ttl_ms','expires_in_ms','count','completed','discarded','rejected'))
    for key in ('state','status','identity_state','voice_state','speaker_state'):
        if key in value:
            output[key]=enum(value[key],IDENTITY_STATES|{'CANDIDATE','CONFIRMED','UNCONFIRMED','ANONYMOUS','MATCH',
                'NO_MATCH','AMBIGUOUS','READY','IDLE','BUSY','WAITING_NAME','SAMPLING_VOICE','WAITING_FACE','COMPLETE',
                'SAMPLING','WAITING_SAVE','UNAVAILABLE','NOT_ENROLLED','ACTIVE','INACTIVE','PAUSED','CLOSED'})
    if 'error' in value:output['error_present']=bool(value['error'])
    return output

boot=Path('/proc/sys/kernel/random/boot_id').read_text().strip()
startup_raw=raw(BUSINESS/'startup/config.json');startup=json.loads(startup_raw)
aura=Path(startup['runtime'])/'aura';pins=startup['component_sha256']
ui_path=aura/'config/board_avatar_gtk.json';ui_raw=raw(ui_path);ui=json.loads(ui_raw)
selected=ui['board_business']['face_readback'];binding_raw=raw(selected['path']);binding=json.loads(binding_raw)
camera_unit=unit('aura-camera-ui.service');gui_unit=unit('aura-avatar-ui.service')
camera_owner=owner(int(camera_unit['MainPID'])) if int(camera_unit['MainPID'])>0 else None
gui_owner=owner(int(gui_unit['MainPID'])) if int(gui_unit['MainPID'])>0 else None
launch_path=Path(startup['runtime'])/'launch.json'
launch=doc(launch_path) if launch_path.is_file() else {}
gtk_owner=owner(int(launch['pid'])) if type(launch.get('pid')) is int and Path('/proc',str(launch['pid'])).exists() else None
source_names=('tools/unified_identity_binding.py','tools/binding_hub_runtime.py','tools/provisional_voice.py',
    'tools/identity_resolution.py','common/profile_access.py','board/runtime/board_business.py',
    'board/runtime/board_speaker_business.py','board/interaction/ui_contract.py')
source_pins={name:{'pin':pins.get(name),'actual':digest(aura/name)} for name in source_names if (aura/name).is_file()}
identity_config=doc(binding['identity_config'])
run_config_path=Path(binding['camera_config']);run_config_sha=digest(run_config_path)
source_counts={'total':len(binding['source_sha256']),'verified':0,'excluded_motor_paths':0}
for path,expected in binding['source_sha256'].items():
    if str(path).startswith('/home/root/aura-pan-wide-'):
        source_counts['excluded_motor_paths']+=1
        continue
    assert digest(path)==expected
    source_counts['verified']+=1
contract_path=aura/'board/interaction/ui_contract.py'
assert source_pins['board/interaction/ui_contract.py']['pin']==source_pins['board/interaction/ui_contract.py']['actual']=='7f67e4bdfe4a95396fbe6445759c80f8ea79cf51d2d991269213409a83daec86'
contract=ast.parse(raw(contract_path).decode('utf-8'));space={'copy':copy,'math':math}
for node in contract.body:
    if isinstance(node,ast.Assign) and len(node.targets)==1 and isinstance(node.targets[0],ast.Name) and node.targets[0].id in ('PROTOCOL','MODULE_STATES','ACTIONS'):
        space[node.targets[0].id]=ast.literal_eval(node.value)
definitions=[copy.deepcopy(node) for node in contract.body if isinstance(node,ast.FunctionDef) and node.name in ('integer','text','require','target_key','validate_snapshot')]
assert len(definitions)==5
exec(compile(ast.Module(body=definitions,type_ignores=[]),str(contract_path)+'::<metadata-validator-only>','exec'),space)

def project(health,snapshot,gui):
    now=round(time.monotonic()*1000)
    valid=True
    try:space['validate_snapshot'](snapshot,boot,now)
    except (ValueError,KeyError,TypeError):valid=False
    modules=obj(snapshot,'modules');identity=obj(modules,'identity');target=obj(modules,'target')
    service=obj(health,'identity');diag=obj(service,'recognition_diagnostics')
    face=identity.get('face_target');source=identity.get('source_mono_ms')
    face_keys=[row.get('key') for row in identity.get('face_targets',[]) if isinstance(row,dict)] if isinstance(identity.get('face_targets'),list) else []
    fresh=valid and type(source) is int and 0<=now-source<int(identity_config['result_ttl_ms']) and face is not None and identity.get('target')==face
    identity_state=enum(identity.get('state'),IDENTITY_STATES)
    feature=obj(service,'feature_inference');face_counts=obj(service,'face_targets')
    camera=numbers(health,('pid','capture_frames','detected_frames','capture_age_ms','observation_age_ms'))
    camera.update(identity_ready=service.get('ready') is True,identity_error_present=bool(service.get('error')),
        camera_error_present=any(bool(health.get(k)) for k in ('camera_error','detector_error','preview_error')),
        sface_counters=numbers(feature,('requests','execution_attempts','completed','features_returned','deferred','slot_denials','expired_after_admission')),
        face_counters=numbers(face_counts,('processed','confirmed','discarded','errors')))
    perception={'snapshot_valid':valid,'actual_source':snapshot.get('source_kind')=='actual',
        'snapshot_age_ms':now-snapshot['observed_mono_ms'] if type(snapshot.get('observed_mono_ms')) is int else None,
        'snapshot_ttl_ms':snapshot.get('ttl_ms') if type(snapshot.get('ttl_ms')) is int else None,
        'face_count':identity.get('face_count') if type(identity.get('face_count')) is int else None,
        'face_target_valid':valid and face is not None and face in face_keys,
        'identity_state':identity_state,'identity_result_fresh':fresh,
        'identity_result_age_ms':now-source if type(source) is int else None,
        'known_fresh':fresh and identity_state=='KNOWN','unknown_fresh':fresh and identity_state=='UNKNOWN',
        'diagnostic_reason':enum(diag.get('reason_code'),REASONS),
        'diagnostic_policy_matches_config':diag.get('threshold')==identity_config['threshold'] and diag.get('ambiguity_margin')==identity_config['ambiguity_margin'],
        'body_target_state':enum(target.get('state'),{'UNKNOWN','NONE','CANDIDATE','CONFIRMED','LOST','AMBIGUOUS'})}
    business=obj(gui,'board_business')
    identity_view={key:safe_result(gui.get(key)) for key in ('identity','speaker','speaker_identity','identity_binding',
        'binding','profile_access','identity_resolution','voice_identity','unified_identity') if isinstance(gui.get(key),dict)}
    identity_view['business_speaker']=safe_result(business.get('speaker'))
    identity_view['business_conversation_selection']=safe_result(business.get('conversation_selection'))
    for key in ('local_transcription','interaction','current_interaction'):
        row=obj(gui,key)
        if row:
            identity_view[key]={name:safe_result(row.get(name)) for name in ('speaker','identity','voice','anonymous','binding','profile_access') if isinstance(row.get(name),dict)}
    return {'board_mono':time.monotonic(),'camera':camera,'perception':perception,
        'gui_identity_projection':identity_view,'gui_business_started':business.get('started') is True,
        'gui_identity_related_top_keys':[key for key in gui if any(fragment in key for fragment in ('identity','speaker','profile','transcription'))]}

samples=[]
for i in range(5):
    h=request(8790,'/health');snapshot=request(8790,'/v1/ui/status')
    try:g=request(8783,'/api/state')
    except (OSError,ValueError,http.client.HTTPException):g={}
    samples.append(project(h,snapshot,g))
    h=None;snapshot=None;g=None
    if i<4:time.sleep(1.5)

camera_after=unit('aura-camera-ui.service');gui_after=unit('aura-avatar-ui.service')
stable=raw(BUSINESS/'startup/config.json')==startup_raw and raw(ui_path)==ui_raw and raw(selected['path'])==binding_raw
query_component=source_pins.get('tools/unified_identity_binding.py',{})
query_current=query_component.get('pin')==query_component.get('actual')==EXPECTED_QUERY_FIX
launch_metadata={key:launch.get(key) for key in ('boot_id','startup_sha256','configuration_sha256','component_manifest_sha256','supervisor_pid','pid') if key in launch}
binding_metadata={key:binding.get(key) for key in ('board_boot_id','camera_pid','camera_start_ticks','camera_cmdline_sha256','result_ttl_ms')}
print(json.dumps({'schema':'aura-visual-identity-language-readonly-1','utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'boot_id':boot,'startup_sha256':hashlib.sha256(startup_raw).hexdigest(),'ui_configuration_sha256':hashlib.sha256(ui_raw).hexdigest(),
    'source_pins':source_pins,'selected_path':selected['path'],'selected_sha256':hashlib.sha256(binding_raw).hexdigest(),
    'selected_declared_sha_matches_actual':selected['sha256']==hashlib.sha256(binding_raw).hexdigest(),
    'selected_sources':source_counts,'selected_camera_binding':binding_metadata,
    'camera_run_config_path':str(run_config_path),'camera_run_config_sha256':run_config_sha,
    'camera_owner':camera_owner,'gui_supervisor_owner':gui_owner,'gtk_owner':gtk_owner,
    'camera_unit':camera_unit,'gui_unit':gui_unit,'camera_unit_after':camera_after,'gui_unit_after':gui_after,
    'launch_metadata':launch_metadata,'launch_top_keys':sorted(launch),
    'identity_policy':{key:identity_config.get(key) for key in ('threshold','ambiguity_margin','result_ttl_ms')},
    'source_snapshot_stable_during_observation':stable,
    'camera_owner_stable':camera_owner is not None and camera_after['MainPID']==str(camera_owner['pid']) and owner(camera_owner['pid'])==camera_owner,
    'query_fix_v2_current_pin_and_file_match':query_current,
    'samples':samples,'raw_names_ids_scores_templates_images_or_dialogue_exported':False,
    'motor_state_or_files_inspected':False,'service_or_database_or_device_operation':False,'board_mutations':False},sort_keys=True))
