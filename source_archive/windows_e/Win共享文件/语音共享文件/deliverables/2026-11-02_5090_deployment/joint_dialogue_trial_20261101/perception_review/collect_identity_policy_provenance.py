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

import re
assert initial_unit['pid']==16314 and initial_unit['active_state']=='active' and initial_unit['sub_state']=='running'
old_path=Path('/home/root/aura-face-follow-test-20261101-bebd3e7d-r2/camera-binding/face_gallery_readback.local.json')
old_sha='a7402eb0f3e8d5391a95136d65759569be86eceeb75d830146a4b1d14cc81667'
assert digest(old_path)==old_sha
old=json.loads(raw(old_path));assert len(old['source_sha256'])==23
assert all(binding['source_sha256'].get(path)==sha for path,sha in old['source_sha256'].items())
identity_path=Path(binding['identity_config'])
assert old['identity_config']==binding['identity_config']
identity_sha=digest(identity_path);policy=json.loads(raw(identity_path))
assert type(policy['threshold']) in (float,int) and type(policy['ambiguity_margin']) in (float,int)
run_path=Path(binding['camera_config']);run=json.loads(raw(run_path))
assert run['identity']=={'enabled':True,'config':str(identity_path)}
native=run['native_execution'];manifest_path=Path(native['source_manifest'])
assert digest(manifest_path)==native['source_manifest_sha256']=='5e08f7cf587d74334ef24104ea01f79701629b48f2004fb772ce3f8ea82afd0d'
pins=json.loads(raw(manifest_path))['files'];native_root=manifest_path.parent/'aura'
assert len(pins)==222
snippets={}
for name in ('board/identity/camera_faces.py','board/identity/store.py','board/identity/live.py'):
    path=native_root/name;content=raw(path)
    assert hashlib.sha256(content).hexdigest()==pins[name]
    text=content.decode();lines=text.splitlines()
    selected_lines=[]
    if name.endswith('camera_faces.py'):
        wanted=re.compile(r'def (config_for|make_identity)|IdentityStore|config\[.(?:threshold|ambiguity_margin|result_ttl_ms|interval_ms|model_id).\]|config_path|identity.*config')
        selected_lines=[{'line':n,'source':line} for n,line in enumerate(lines,1) if wanted.search(line)]
    elif name.endswith('store.py'):
        wanted=re.compile(r'def __init__|self\.threshold|self\.ambiguity_margin|def match|scored\[0\]\[0\]|return IdentityMatch')
        selected_lines=[{'line':n,'source':line} for n,line in enumerate(lines,1) if wanted.search(line)]
    else:
        tree=ast.parse(text)
        klass=next(node for node in tree.body if isinstance(node,ast.ClassDef) and node.name=='IdentityService')
        for node in klass.body:
            if isinstance(node,ast.FunctionDef) and node.name in ('_fresh','view'):
                for n in range(node.lineno,node.end_lineno+1):
                    if node.name=='_fresh' or any(token in lines[n-1] for token in ('fresh','state','result[','source_mono_ms','source_frame_id','target=','return value')):
                        selected_lines.append({'line':n,'source':lines[n-1]})
        diagnostic_present=any(isinstance(node,ast.FunctionDef) and node.name=='recognition_diagnostics' for node in klass.body)
    snippets[name]={'path':str(path),'sha256':pins[name],'selected_public_source_lines':selected_lines}
config_pins={'old_23pin':old['source_sha256'].get(str(identity_path)),
             'new_24pin':binding['source_sha256'].get(str(identity_path)),
             'actual_file':identity_sha}
cmd=(Path('/proc/1333')/'cmdline').read_bytes().split(b'\0')
identity_health=request(8790,'/health').get('identity',{})
assert isinstance(identity_health,dict)
assert digest(STARTUP if 'STARTUP' in globals() else BUSINESS/'startup/config.json')==STARTUP_SHA
assert digest(old_path)==old_sha and digest(SELECTED)==SELECTED_SHA and digest(identity_path)==identity_sha
print(json.dumps({'schema':'aura-joint-trial-identity-policy-provenance-1',
    'board_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'boot_id':BOOT,
    'startup_sha256':STARTUP_SHA,'old_binding_path':str(old_path),'old_binding_sha256':old_sha,
    'new_binding_path':str(SELECTED),'new_binding_sha256':SELECTED_SHA,
    'identity_config_path':str(identity_path),'identity_config_sha256':identity_sha,
    'direct_json_field_names':['threshold','ambiguity_margin','result_ttl_ms'],
    'direct_numeric_values':{key:policy[key] for key in ('threshold','ambiguity_margin','result_ttl_ms')},
    'configuration_source_pins':config_pins,
    'same_config_sha_in_old_23_new_24_and_actual':len(set(config_pins.values()))==1 and None not in config_pins.values(),
    'all_old_23_source_pins_unchanged_in_new_24':True,
    'actual_camera_run_config_path':str(run_path),'actual_camera_run_config_sha256':digest(run_path),
    'camera_command_contains_actual_run_config_path':str(run_path).encode() in cmd,
    'actual_camera_run_config_selects_same_identity_path':True,
    'native_source_manifest_sha256':native['source_manifest_sha256'],'source_read_path_evidence':snippets,
    'native_live_has_recognition_diagnostics_method':diagnostic_present,
    'health_has_recognition_diagnostics_object':isinstance(identity_health.get('recognition_diagnostics'),dict),
    'model_chain_ready':identity_health.get('ready') is True and not identity_health.get('error'),
    'board_mutations':False,'configuration_changed':False,'database_opened':False,
    'registration_or_recording_or_playback_or_motion_requested':False,
    'names_ids_templates_photos_similarity_scores_or_dialogue_exported':False},sort_keys=True))
