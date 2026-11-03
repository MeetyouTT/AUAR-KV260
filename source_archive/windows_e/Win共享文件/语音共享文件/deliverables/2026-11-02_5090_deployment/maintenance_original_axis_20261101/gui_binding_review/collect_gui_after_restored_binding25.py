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
STARTUP_SHA='3f5e81abc20ce5169ac91ae302611cba8958175a6a2bdb615fd9b858353120d5'
UI_SHA='fc98455a5586cc4f1896f5472ec9b204bd7ff2b0c5be2798ba5cab1788b9b959'
SELECTED=Path('/home/root/aura-5090-recovery-20261102-903cfade/gui-selected-79866-25pins-v1/face_gallery_readback.local.json')
SELECTED_SHA='9ab2533d2c3000d61095f54de2e8199f53461ac085e2f58230ab36149be6af1f'
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
    assert value.get('pid')==79866 and value.get('board_boot_id')==BOOT
    assert process(79866)=={'pid':79866,'birth_ticks':'2265436','command_sha256':CAM_CMD_SHA}
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

def platform():
    assert Path('/proc/device-tree/fpga-full/firmware-name').read_bytes().rstrip(b'\0') == b'aura-visual-servo-b4096-wide-v1.bit.bin'
    assert Path('/sys/class/fpga_manager/fpga0/state').read_text().strip() == 'operating'
    assert Path('/etc/vart.conf').read_bytes() == b'firmware: /lib/firmware/xilinx/aura-visual-servo-b4096-wide-v1/aura-visual-servo-b4096-wide-v1.xclbin\n'
    assert digest('/sys/firmware/fdt') == 'd68bc147f22f5ab23bc60f0c2762af4bcd7b64340953e9c948e28ffa6b80f7ca'
    overlays = Path('/sys/kernel/config/device-tree/overlays')
    assert sorted(p.name for p in overlays.iterdir()) == ['aura-visual-servo-b4096-wide-v1_image_1']
    assert (overlays/'aura-visual-servo-b4096-wide-v1_image_1/status').read_text().strip() == 'applied'
    assert Path('/sys/bus/platform/drivers/zocl-drm/axi:zyxclmm_drm').resolve(strict=True) == Path('/sys/devices/platform/axi/axi:zyxclmm_drm')
    assert Path('/sys/class/drm/renderD128/device').resolve(strict=True) == Path('/sys/devices/platform/axi/axi:zyxclmm_drm')

platform()
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==BOOT
assert digest(BUSINESS/'startup/config.json')==STARTUP_SHA
startup=json.loads(raw(BUSINESS/'startup/config.json'));AURA=Path(startup['runtime'])/'aura'
assert len(startup['component_sha256'])==380
assert all(digest(AURA/name)==sha for name,sha in startup['component_sha256'].items())
assert digest(AURA/'config/board_avatar_gtk.json')==UI_SHA
assert digest(AURA/'config/face_gallery_readback.local.json')==DEFAULT_SHA
assert digest(SELECTED)==SELECTED_SHA
assert json.loads(raw(AURA/'config/board_avatar_gtk.json'))['board_business']['face_readback']=={'path':str(SELECTED),'sha256':SELECTED_SHA}
binding=json.loads(raw(SELECTED));assert len(binding['source_sha256'])==25
path=AURA/'board/runtime/audio/face_gallery_readback.py';assert digest(path)==VERIFIER_SHA
tree=ast.parse(raw(path).decode());klass=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='FaceGalleryReadback')
node=copy.deepcopy(next(n for n in klass.body if isinstance(n,ast.FunctionDef) and n.name=='_verify'));node.decorator_list=[]
space={'Path':Path,'hashlib':hashlib,'json':json}
exec(compile(ast.Module(body=[node],type_ignores=[]),str(path)+'::<metadata-only-_verify>','exec'),space)
space['_verify'](binding)
firmware=Path('/proc/device-tree/fpga-full/firmware-name').read_bytes().rstrip(b'\0').decode()
assert firmware=='aura-visual-servo-b4096-wide-v1.bit.bin'
assert json.loads(raw('/home/root/.local/share/aura-board-business/listening_preference.json'))=={'version':1,'enabled':False}
initial_unit=unit('aura-avatar-ui.service')
owners={}
if initial_unit['pid']>0:
    owners['supervisor']=process(initial_unit['pid'])
    launch=json.loads(raw(Path(startup['runtime'])/'launch.json'))
    assert launch['boot_id']==BOOT and launch['supervisor_pid']==initial_unit['pid']
    assert launch['service']=='aura-avatar-ui.service'
    owners['gtk']=process(launch['pid'])
samples=[]
for i in range(3):
    sample={'board_mono':time.monotonic(),'camera':camera(request(8790,'/health'))}
    try:sample['gui']=gui(request(8783,'/api/state'))
    except (OSError,ValueError,AssertionError,http.client.HTTPException) as exc:
        sample['gui_unavailable_error_type']=type(exc).__name__
    samples.append(sample)
    if i<2:time.sleep(1.2)
final_unit=unit('aura-avatar-ui.service');camera_unit=unit('aura-camera-ui.service')
stable_owners=initial_unit['pid']==final_unit['pid'] and all(process(item['pid'])==item for item in owners.values())
maps=native_map_owners()
assert digest(BUSINESS/'startup/config.json')==STARTUP_SHA
assert all(digest(AURA/name)==sha for name,sha in startup['component_sha256'].items())
space['_verify'](binding)
assert Path('/proc/device-tree/fpga-full/firmware-name').read_bytes().rstrip(b'\0').decode()==firmware
saved=json.loads(raw('/home/root/.local/share/aura-board-business/listening_preference.json'))
assert saved=={'version':1,'enabled':False}
gs=[sample['gui'] for sample in samples if 'gui' in sample]
last=gs[-1] if gs else {};hf=last.get('handsfree',{});biz=last.get('board_business',{});pan=last.get('manual_pan',{})
display=last.get('avatar_display',{});pair=last.get('character_pair',{})
checks={
    'unit_active_running':final_unit['active_state']=='active' and final_unit['sub_state']=='running' and not final_unit['job_pending'],
    'stable_supervisor_and_gtk_owner':bool(owners) and stable_owners,
    'all_three_gui_samples_available':len(gs)==3,
    'api_sequence_advancing':len(gs)==3 and type(gs[0].get('sequence')) is int and gs[-1].get('sequence',0)>gs[0]['sequence'],
    'main_page':last.get('ui_page')=='main',
    'original_pair_ready':pair.get('state')=='READY' and pair.get('production_selected') is True and pair.get('fallback_allowed') is False and not pair.get('error_present'),
    'native_avatar_visible_and_advancing':len(gs)==3 and display.get('visible') is True and display.get('presentation_state')=='visible' and type(gs[0].get('avatar_display',{}).get('frames')) is int and display.get('frames',0)>gs[0]['avatar_display']['frames'],
    'no_runtime_faults':last.get('runtime_fault_count')==0,
    'paused_microphone_closed':hf.get('enabled') is False and hf.get('state')=='PAUSED' and hf.get('microphone_open') is False,
    'no_playback':last.get('playing') is False and last.get('phase')=='IDLE',
    'board_business_started':biz.get('started') is True and biz.get('closed') is False and biz.get('data_origin')=='board' and biz.get('production_cutover') is True and biz.get('writer',{}).get('held') is True and biz.get('receipt',{}).get('verified') is True,
    'business_clock_anchored':biz.get('clock',{}).get('anchored') is True and biz.get('clock',{}).get('event_time_available') is True and biz.get('clock',{}).get('same_boot') is True,
    'old_axis_context_guard_keeps_connection_unavailable':pan.get('state') in ('FAULT','UNAVAILABLE') and pan.get('automatic_following') is False and pan.get('readback_present') is False and pan.get('pulse_us') is None,
    'no_vsrv_library_or_dev_mem_mapped':not maps,
    'camera_running_and_advancing':camera_unit['pid']==79866 and camera_unit['active_state']=='active' and samples[-1]['camera'].get('capture_frames',0)>samples[0]['camera'].get('capture_frames',0) and samples[-1]['camera'].get('detected_frames',0)>samples[0]['camera'].get('detected_frames',0),
    'camera_no_errors_or_motion':all(not x['camera'].get('camera_error_present') and not x['camera'].get('identity_error_present') and x['camera'].get('identity_ready') is True and x['camera'].get('motion_command_emitted') is False for x in samples),
}
print(json.dumps({'schema':'aura-gui-restored-camera-post-start-filtered-metadata-2',
    'status':'GUI_SOFTWARE_READY_PAUSED_OLD_AXIS_CONTEXT_LOCKED' if all(checks.values()) else 'OBSERVED_NOT_ALL_SOFTWARE_READY',
    'board_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'boot_id':BOOT,
    'startup_sha256':STARTUP_SHA,'ui_config_sha256':UI_SHA,'selected_binding_sha256':SELECTED_SHA,
    'components_verified':380,'selected_source_files_verified':25,'original_verifier_passed':True,
    'gui_unit_initial':initial_unit,'gui_unit_final':final_unit,'camera_unit':camera_unit,
    'owners':owners,'samples':samples,'checks':checks,'native_register_map_owners':maps,
    'saved_listening_enabled':False,'firmware':'aura-visual-servo-b4096-wide-v1.bit.bin',
    'physical_panel_observed':False,'board_mutations':False,'project_imported':False,
    'database_opened':False,'text_or_images_or_templates_exported':False,'commands_sent':False},sort_keys=True))
