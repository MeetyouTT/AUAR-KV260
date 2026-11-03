"""Read-only software startup observation. Never saves raw state, text, IDs, frames or templates."""
import ast
import copy
import datetime
import hashlib
import http.client
import json
from pathlib import Path
import subprocess
import time

BOOT='903cfade-b93c-48fa-804e-379be1967313'
BUSINESS=Path('/home/root/aura-board-business-20261030/production-5259eab11e42af13')
STARTUP_SHA='3fd124287463650f48232cb387c78d01399bad7ddcda483db725163298de4591'
UI_SHA='fc21e6f2ef831442b08966957fa7aeb744a9b74124ee8778edc40397285626cd'
SELECTED=Path('/home/root/aura-5090-recovery-20261102-903cfade/gui-selected-1333-24pins-v1/face_gallery_readback.local.json')
SELECTED_SHA='4d8f0c2bccea1c7a56761fbcb204f40ba3b3c2fc9efad76af778aff535d378ac'
DEFAULT_SHA='e203e6ffe973397464791eb07f12e0bd0c24658988c119e9d7d75685c4e41986'
VERIFIER_SHA='b77c32b3863b9464006ac1bb7f16c8f767113925d9142d77e4755f1ce365527e'
CAM_CMD_SHA='acf3ee123d7674fdea6e90e79252909ca396249c870269169910879d940c27dd'

def raw(path):
    p=Path(path)
    assert p.is_file() and not p.is_symlink() and p.suffix not in ('.db','.sqlite','.sqlite3')
    assert p.stat().st_size <= 64000000
    return p.read_bytes()

def digest(path):return hashlib.sha256(raw(path)).hexdigest()

def request(port,path):
    c=http.client.HTTPConnection('127.0.0.1',port,timeout=3)
    try:
        c.request('GET',path);r=c.getresponse();body=r.read(2097153)
        assert r.status == 200 and len(body) <= 2097152
        value=json.loads(body);assert isinstance(value,dict)
        return value
    finally:c.close()

def unit(name):
    p=subprocess.run(['systemctl','show',name,
        '--property=MainPID,Job,ActiveState,SubState,Result,ExecMainStatus'],
        capture_output=True,text=True,timeout=5)
    assert p.returncode == 0
    v=dict(line.split('=',1) for line in p.stdout.splitlines() if '=' in line)
    assert set(v) == {'MainPID','Job','ActiveState','SubState','Result','ExecMainStatus'}
    return {'pid':int(v['MainPID']),'job_pending':bool(v['Job']),
        'active_state':enum(v['ActiveState'],{'active','activating','inactive','failed','deactivating'}),
        'sub_state':enum(v['SubState'],{'running','start','start-pre','stop','dead','failed','exited'}),
        'result':enum(v['Result'],{'success','exit-code','timeout','signal','resources','start-limit-hit'}),
        'exec_main_status':int(v['ExecMainStatus'])}

def enum(value,allowed):return value if type(value) is str and value in allowed else None

def selected(value,keys):
    if not isinstance(value,dict):return {}
    return {key:value[key] for key in keys if key in value and (value[key] is None or type(value[key]) in (bool,int,float))}

def obj(value,key):
    result=value.get(key,{}) if isinstance(value,dict) else {}
    return result if isinstance(result,dict) else {}

def process(pid):
    p=Path('/proc')/str(pid)
    return {'pid':pid,'birth_ticks':(p/'stat').read_text().rsplit(')',1)[1].split()[19],
            'command_sha256':hashlib.sha256((p/'cmdline').read_bytes()).hexdigest()}

def camera(value):
    assert value.get('pid')==1333 and value.get('board_boot_id')==BOOT
    assert process(1333)=={'pid':1333,'birth_ticks':'2359','command_sha256':CAM_CMD_SHA}
    result=selected(value,('pid','capture_frames','detected_frames','capture_age_ms','observation_age_ms','motion_command_emitted'))
    result.update(identity_ready=obj(value,'identity').get('ready') is True,
                  identity_error_present=bool(obj(value,'identity').get('error')),
                  camera_error_present=any(bool(value.get(k)) for k in ('camera_error','detector_error','preview_error')))
    return result

def gui(value):
    pair=obj(value,'character_pair');display=obj(value,'avatar_display')
    hands=obj(value,'handsfree_dialogue');manual=obj(value,'manual_pan');business=obj(value,'board_business')
    result=selected(value,('sequence','playing','paused'))
    result.update(backend=enum(value.get('backend'),{'gtk3-gstreamer'}),
        ui_page=enum(value.get('ui_page'),{'main','vision','settings','history','profiles','memory'}),
        phase=enum(value.get('phase'),{'IDLE','VOICE_PREPARING','VOICE_STARTING','SPEAKING','ACTION','DIALOGUE_WAITING'}),
        runtime_fault_count=obj(value,'runtime_faults').get('count') if type(obj(value,'runtime_faults').get('count')) is int else None,
        character_pair=dict(selected(pair,('selected','production_selected','fallback_allowed','target_fps')),
                            state=enum(pair.get('state'),{'PREPARED','READY','FAILED'}),error_present=bool(pair.get('error'))),
        avatar_display=dict(selected(display,('frames','visible','age_ms','target_fps','frame_scheduling_active')),
            presentation_state=enum(display.get('presentation_state'),{'visible','hidden'})),
        handsfree=dict(selected(hands,('enabled','microphone_open','voice_barge_in')),
            state=enum(hands.get('state'),{'PAUSED','WAITING_SERVICE','WAITING_SPEECH','WAITING_WAKE','COOLDOWN','CONVERSATION'}),
            error_present=bool(hands.get('error'))),
        local_recording=dict(state=enum(obj(value,'local_recording').get('state'),{'IDLE','READY','RECORDING','ERROR','STOPPING'}),
            error_present=bool(obj(value,'local_recording').get('error'))),
        manual_pan=dict(selected(manual,('automatic_following','pulse_us','target_us','backend_pid')),
            state=enum(manual.get('state'),{'CONNECTING','FAULT','UNAVAILABLE','READY','MOVING','CLOSED','STOPPING'}),
            readback_present=isinstance(manual.get('readback'),dict),
            error_present=bool(manual.get('error')),history_length=len(manual['history']) if isinstance(manual.get('history'),list) else None),
        board_business=dict(selected(business,('started','closed','production_cutover')),
            data_origin=enum(business.get('data_origin'),{'board'}),
            writer=selected(obj(business,'writer'),('held',)),
            receipt=selected(obj(business,'receipt'),('verified',)),
            clock=selected(obj(business,'clock'),('anchored','event_time_available','safe_for_compaction','persistent','same_boot')),
            speaker=selected(obj(business,'speaker'),('ready','queued_or_active')),
            memory=selected(obj(business,'memory'),('queued','active','completed','discarded','failure_streak'))))
    return result

def native_map_owners():
    owners=[]
    for p in Path('/proc').iterdir():
        if not p.name.isdigit():continue
        try:text=(p/'maps').read_text()
        except (FileNotFoundError,ProcessLookupError):continue
        except PermissionError:raise RuntimeError('Cannot audit native register owners') from None
        if 'libvsrv.so' in text or '/dev/mem' in text:
            owners.append({'pid':int(p.name),'vsrv_library_mapped':'libvsrv.so' in text,'dev_mem_mapped':'/dev/mem' in text})
    return owners

assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==BOOT
assert digest(BUSINESS/'startup/config.json')==STARTUP_SHA
startup=json.loads(raw(BUSINESS/'startup/config.json'));AURA=Path(startup['runtime'])/'aura'
assert len(startup['component_sha256'])==380
assert all(digest(AURA/name)==sha for name,sha in startup['component_sha256'].items())
assert digest(AURA/'config/board_avatar_gtk.json')==UI_SHA
assert digest(AURA/'config/face_gallery_readback.local.json')==DEFAULT_SHA
assert digest(SELECTED)==SELECTED_SHA
assert json.loads(raw(AURA/'config/board_avatar_gtk.json'))['board_business']['face_readback']=={'path':str(SELECTED),'sha256':SELECTED_SHA}
binding=json.loads(raw(SELECTED));assert len(binding['source_sha256'])==24
path=AURA/'board/runtime/audio/face_gallery_readback.py';assert digest(path)==VERIFIER_SHA
tree=ast.parse(raw(path).decode());klass=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='FaceGalleryReadback')
node=copy.deepcopy(next(n for n in klass.body if isinstance(n,ast.FunctionDef) and n.name=='_verify'));node.decorator_list=[]
space={'Path':Path,'hashlib':hashlib,'json':json}
exec(compile(ast.Module(body=[node],type_ignores=[]),str(path)+'::<metadata-only-_verify>','exec'),space)
space['_verify'](binding)
firmware=Path('/proc/device-tree/fpga-full/firmware-name').read_bytes().rstrip(b'\0').decode()
assert firmware=='kv260-benchmark-b4096.bit.bin'
assert json.loads(raw('/home/root/.local/share/aura-board-business/listening_preference.json'))=={'version':1,'enabled':False}
initial_unit=unit('aura-avatar-ui.service')
owners={}
if initial_unit['pid']>0:
    owners['supervisor']=process(initial_unit['pid'])
    launch=json.loads(raw(Path(startup['runtime'])/'launch.json'))
    assert launch['boot_id']==BOOT and launch['supervisor_pid']==initial_unit['pid']
    assert launch['service']=='aura-avatar-ui.service'
    owners['gtk']=process(launch['pid'])

# Additional joint-trial readiness projection. No raw API state leaves board RAM.
import math
assert initial_unit['pid']==16314 and initial_unit['active_state']=='active' and initial_unit['sub_state']=='running'
assert owners=={
    'supervisor':{'pid':16314,'birth_ticks':'1738385','command_sha256':'48a28efa32b2050901e73e85a80a30a90dcfbce0b7249bde5d6d90902740631d'},
    'gtk':{'pid':16318,'birth_ticks':'1738515','command_sha256':'0773efafd4a34e1785cf7f7dd51398d591a7de42f40f7c169997118a47458963'}}
identity_config=json.loads(raw(binding['identity_config']))
# Report the actual pinned policy; never repair or relabel a mismatch to assumed history.
assert type(identity_config['threshold']) in (int,float) and type(identity_config['ambiguity_margin']) in (int,float)
assert identity_config['result_ttl_ms']==binding['result_ttl_ms']==3000
run_config=json.loads(raw(binding['camera_config']))
native=run_config['native_execution']
assert digest(native['source_manifest'])==native['source_manifest_sha256']=='5e08f7cf587d74334ef24104ea01f79701629b48f2004fb772ce3f8ea82afd0d'
native_root=Path(native['source_manifest']).parent/'aura'
native_pins=json.loads(raw(native['source_manifest']))['files']
assert len(native_pins)==222
assert {str(p.relative_to(native_root)):digest(p) for p in native_root.rglob('*.py') if not p.is_symlink()}==native_pins
identity_source_sha=digest(native_root/'board/identity/live.py')
identity_source_matches_reviewed=identity_source_sha=='1dadec0e22e7b1a03e5aafe904ea8eea5f8902f8c9ce29b5873d31995d111c10'
contract=AURA/'board/interaction/ui_contract.py'
assert digest(contract)=='7f67e4bdfe4a95396fbe6445759c80f8ea79cf51d2d991269213409a83daec86'
contract_ast=ast.parse(raw(contract).decode())
contract_space={'copy':copy,'math':math}
for node in contract_ast.body:
    if isinstance(node,ast.Assign) and len(node.targets)==1 and isinstance(node.targets[0],ast.Name) and node.targets[0].id in ('PROTOCOL','MODULE_STATES','ACTIONS'):
        contract_space[node.targets[0].id]=ast.literal_eval(node.value)
functions=[copy.deepcopy(node) for node in contract_ast.body if isinstance(node,ast.FunctionDef) and node.name in ('integer','text','require','target_key','validate_snapshot')]
assert len(functions)==5
exec(compile(ast.Module(body=functions,type_ignores=[]),str(contract)+'::<snapshot-only-original-validator>','exec'),contract_space)
reasons={'WAITING_FRAME','SERVICE_ERROR','MODEL_LOADING','MULTIPLE_FACES','TARGET_UNCONFIRMED',
    'NO_FACE_OR_TARGET','STALE_OR_FOREIGN_RESULT','MATCHED','AMBIGUOUS','EMPTY_GALLERY',
    'LOW_SIMILARITY','FEATURE_OR_QUALITY_UNAVAILABLE'}

def perception(health,snapshot):
    now=round(time.monotonic()*1000)
    valid=True
    try:contract_space['validate_snapshot'](snapshot,BOOT,now)
    except (ValueError,KeyError,TypeError):valid=False
    modules=obj(snapshot,'modules');ident=obj(modules,'identity');target=obj(modules,'target')
    vision=obj(modules,'vision');camera_module=obj(modules,'camera')
    health_identity=obj(health,'identity');diag=obj(health_identity,'recognition_diagnostics')
    face=ident.get('face_target');body=target.get('selected')
    face_keys=[row.get('key') for row in ident.get('face_targets',[]) if isinstance(row,dict)] if isinstance(ident.get('face_targets'),list) else []
    body_keys=[row.get('key') for row in target.get('tracks',[]) if isinstance(row,dict)] if isinstance(target.get('tracks'),list) else []
    source=ident.get('source_mono_ms');age=now-source if type(source) is int else None
    fresh=valid and type(age) is int and 0<=age<3000 and face is not None and ident.get('target')==face
    ready=health_identity.get('ready') is True and not health_identity.get('error')
    reason=enum(diag.get('reason_code'),reasons)
    state=enum(ident.get('state'),{'UNKNOWN','KNOWN','ENROLLING','DELETED','ERROR'})
    if not valid:classification='SNAPSHOT_EXPIRED_OR_INVALID'
    elif not ready:classification='MODEL_LOADING_OR_SERVICE_ERROR'
    elif face is None:classification='NO_TARGET' if ident.get('face_count',0)==0 else 'TARGET_UNCONFIRMED_OR_MULTIPLE'
    elif reason=='STALE_OR_FOREIGN_RESULT' and not fresh:classification='RESULT_EXPIRED_OR_FOREIGN'
    elif fresh and state=='KNOWN':classification='KNOWN_FRESH'
    elif fresh and state=='UNKNOWN':classification='UNKNOWN_FRESH'
    elif type(age) is int and not 0<=age<3000:classification='RESULT_EXPIRED'
    else:classification='WAITING_FRESH_RESULT'
    return {'snapshot_original_validator_passed':valid,
        'snapshot_source_actual':snapshot.get('source_kind')=='actual',
        'snapshot_age_ms':now-snapshot['observed_mono_ms'] if type(snapshot.get('observed_mono_ms')) is int else None,
        'snapshot_ttl_ms':snapshot.get('ttl_ms') if type(snapshot.get('ttl_ms')) is int else None,
        'camera_state':enum(camera_module.get('state'),{'UNKNOWN','READY','LOST','ERROR'}),
        'vision_state':enum(vision.get('state'),{'UNKNOWN','READY','DEGRADED','ERROR'}),
        'people_count':vision.get('people_count') if type(vision.get('people_count')) is int else None,
        'body_target_state':enum(target.get('state'),{'UNKNOWN','NONE','CANDIDATE','CONFIRMED','LOST','AMBIGUOUS'}),
        'body_target_valid':valid and body is not None and body in body_keys and target.get('state')=='CONFIRMED',
        'body_track_count':len(body_keys),'face_count':ident.get('face_count') if type(ident.get('face_count')) is int else None,
        'face_target_valid':valid and face is not None and face in face_keys,
        'identity_chain_ready':ready,'identity_backend_original':health_identity.get('backend')=='DPU_SFACE_INT8',
        'identity_state':state,'identity_result_classification':classification,
        'identity_result_fresh_and_current_target':fresh,
        'identity_result_age_ms':age,'identity_diagnostic_reason':reason,
        'actually_recognized_in_this_sample':ready and fresh and state=='KNOWN',
        'identity_processed':health_identity.get('processed') if type(health_identity.get('processed')) is int else None,
        'identity_discarded':health_identity.get('discarded') if type(health_identity.get('discarded')) is int else None,
        'threshold_is_original_085':identity_config['threshold']==.85,
        'ambiguity_margin_is_original_010':identity_config['ambiguity_margin']==.1,
        'result_ttl_is_original_3000ms':identity_config['result_ttl_ms']==3000,
        'health_diagnostic_threshold_matches_original':diag.get('threshold')==.85 and diag.get('ambiguity_margin')==.1}

def character(value):
    result=gui(value)
    result['audio_output_state']=enum(value.get('audio_output_state'),{'NULL','EOS','IDLE_READY','ERROR','PAUSED','PLAYING','WAITING_PCM'})
    result['audio_output']=selected(obj(value,'audio_output'),('underrun_packets','turn_underrun_packets','queued_ms','max_poll_gap_ms','turn_late_rebases'))
    result['mouth_metrics']=selected(value,('mouth_level','speech_gain'))
    result['native_mouth_metrics']=selected(obj(value,'avatar_display'),('mouth','eye','rejected_controls','stale_frames','model_eye_policy','model_expression'))
    result['playback_error_present']=bool(value.get('error'))
    result['mouth_sync_actually_exercised_in_this_observation']=False
    return result

samples=[]
for i in range(3):
    h=request(8790,'/health');u=request(8790,'/v1/ui/status');g=request(8783,'/api/state')
    samples.append({'board_mono':time.monotonic(),'camera':camera(h),'perception':perception(h,u),'gui':character(g)})
    h=None;u=None;g=None
    if i<2:time.sleep(1.2)
audio_worker=[]
for p in Path('/proc').iterdir():
    if not p.name.isdigit():continue
    try:
        fields=(p/'stat').read_text().rsplit(')',1)[1].split()
        if int(fields[1])!=16318:continue
        args=(p/'cmdline').read_bytes().split(b'\0')
        if not any(item.endswith(b'/gstreamer_audio_worker.py') for item in args):continue
        audio_worker.append(dict(process(int(p.name)),mcp01_device_selected=b'hw:CARD=MCP01,DEV=0' in args,persistent_mode_selected=b'--persistent' in args))
    except (FileNotFoundError,ProcessLookupError):continue
assert all(process(item['pid'])==item for item in owners.values())
assert digest(BUSINESS/'startup/config.json')==STARTUP_SHA
assert all(digest(AURA/name)==sha for name,sha in startup['component_sha256'].items())
space['_verify'](binding)
assert {str(p.relative_to(native_root)):digest(p) for p in native_root.rglob('*.py') if not p.is_symlink()}==native_pins
final_unit=unit('aura-avatar-ui.service')
last=samples[-1];first=samples[0]
checks={
    'gui_active_running':final_unit['active_state']=='active' and final_unit['sub_state']=='running' and not final_unit['job_pending'],
    'main_page_and_original_role_ready':last['gui'].get('ui_page')=='main' and last['gui']['character_pair'].get('state')=='READY' and last['gui']['character_pair'].get('production_selected') is True,
    'visible_native_animation_advancing':last['gui']['avatar_display'].get('visible') is True and last['gui']['avatar_display'].get('frames',0)>first['gui']['avatar_display'].get('frames',0),
    'no_gui_runtime_faults':all(x['gui'].get('runtime_fault_count')==0 for x in samples),
    'camera_and_detection_advancing':last['camera'].get('capture_frames',0)>first['camera'].get('capture_frames',0) and last['camera'].get('detected_frames',0)>first['camera'].get('detected_frames',0),
    'camera_no_error_or_motion':all(not x['camera'].get('camera_error_present') and x['camera'].get('motion_command_emitted') is False for x in samples),
    'identity_model_chain_ready':all(x['perception']['identity_chain_ready'] and x['perception']['identity_backend_original'] for x in samples),
    'original_identity_threshold_margin_ttl_preserved':all(x['perception']['threshold_is_original_085'] and x['perception']['ambiguity_margin_is_original_010'] and x['perception']['result_ttl_is_original_3000ms'] for x in samples),
    'public_camera_snapshots_fresh_and_valid':all(x['perception']['snapshot_original_validator_passed'] and x['perception']['snapshot_source_actual'] for x in samples),
    'playback_device_software_ready':len(audio_worker)==1 and audio_worker[0]['mcp01_device_selected'] and audio_worker[0]['persistent_mode_selected'] and all(x['gui']['audio_output_state']=='IDLE_READY' and not x['gui']['playback_error_present'] for x in samples),
    'paused_mic_closed_no_playback':all(x['gui']['handsfree'].get('enabled') is False and x['gui']['handsfree'].get('state')=='PAUSED' and x['gui']['handsfree'].get('microphone_open') is False and x['gui'].get('playing') is False and x['gui'].get('phase')=='IDLE' for x in samples),
    'board_business_clock_ready':all(x['gui']['board_business']['clock'].get('anchored') is True and x['gui']['board_business']['clock'].get('event_time_available') is True and x['gui']['board_business']['clock'].get('same_boot') is True for x in samples),
}
print(json.dumps({'schema':'aura-joint-trial-perception-readonly-1',
    'status':'PERCEPTION_ROLE_AUDIO_SOFTWARE_READY' if all(checks.values()) else 'PERCEPTION_REVIEW_HAS_PENDING_CONDITIONS',
    'board_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'boot_id':BOOT,
    'startup_sha256':STARTUP_SHA,'ui_config_sha256':UI_SHA,'selected_binding_sha256':SELECTED_SHA,
    'component_files_verified':380,'selected_camera_source_pins_verified':24,'native_python_files_verified':222,
    'original_selected_binding_verifier_passed':True,'identity_source_sha256':identity_source_sha,
    'identity_source_matches_reviewed_local_source':identity_source_matches_reviewed,
    'actual_pinned_identity_policy':{'threshold':identity_config['threshold'],
        'ambiguity_margin':identity_config['ambiguity_margin'],'result_ttl_ms':identity_config['result_ttl_ms']},
    'owners':owners,'camera_owner':process(1333),'audio_workers':audio_worker,'gui_unit':final_unit,
    'checks':checks,'samples':samples,
    'known_fresh_sample_count':sum(x['perception']['actually_recognized_in_this_sample'] for x in samples),
    'valid_face_target_sample_count':sum(x['perception']['face_target_valid'] for x in samples),
    'valid_body_target_sample_count':sum(x['perception']['body_target_valid'] for x in samples),
    'mouth_sync_or_acoustic_playback_test_performed':False,'physical_role_page_visible_user_reported':True,
    'physical_panel_observed_by_agent':False,'board_mutations':False,'commands_sent':False,
    'recording_or_playback_started':False,'project_imported':False,'database_opened':False,
    'names_ids_templates_images_scores_dialogue_exported':False},sort_keys=True))
