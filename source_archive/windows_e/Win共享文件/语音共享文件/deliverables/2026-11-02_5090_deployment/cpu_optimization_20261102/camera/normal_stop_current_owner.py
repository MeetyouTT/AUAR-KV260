"""Fresh-owner adaptation of the original camera normal-stop procedure.

Default is a read-only dry-run. Only --stop creates one durable stop intent and
submits the original systemctl stop --no-block once. The 25-second observation
deadline never changes systemd's infinite, no-SIGKILL shutdown protection.
Full original reader/history validation is still required after a fresh final.
No Native import, model loading, checkpoint/marker write, motion or DFX occurs.
"""
import argparse
import ast
import copy
import hashlib
import http.client
import json
import os
from pathlib import Path
import stat
import subprocess
import time

CHECKPOINT=Path('/home/root/aura-native-live-20261024/candidates/native-r4-metrics-fix/state/native-protection-checkpoint.json')
FEATURES=('requests','execution_attempts','completed','features_returned','deferred','slot_denials','expired_after_admission')
OPERATOR=Path('/home/root/aura-native-live-20261024/ops/be72669aa53de735/pan-face-edge-v5/native-operator-v1')
NATIVE_UNIT='7cf7eaeecd70e62301d3e12e95d5df6a23bd3e5847ed854200c712598b703c32'
NATIVE_LIBRARY='704f561a50b5f0fb8f9b4cf72c024acce0cdafd888cad0784507f484518fc224'

def require(value,reason):
    if not value:raise RuntimeError(reason)

def regular(path,limit=67108864):
    path=Path(path)
    require(path.is_absolute() and path.resolve()==path and not path.is_symlink(),'Redirected metadata path')
    fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW)
    with os.fdopen(fd,'rb') as f:
        a=os.fstat(f.fileno());require(stat.S_ISREG(a.st_mode) and a.st_size<=limit,'Invalid metadata shape')
        value=f.read(limit+1);b=os.fstat(f.fileno())
    require(len(value)<=limit and (a.st_dev,a.st_ino,a.st_size,a.st_mtime_ns)==(b.st_dev,b.st_ino,b.st_size,b.st_mtime_ns),'Metadata changed during read')
    return value

def digest(value):return hashlib.sha256(value).hexdigest()

def unit(name):
    r=subprocess.run(['systemctl','show',name,'--property=MainPID,ActiveState,SubState,Job,Result,ExecMainStatus,Restart,SendSIGKILL,KillMode,TimeoutStopUSec'],capture_output=True,text=True,timeout=5)
    require(r.returncode==0,'Cannot read service state')
    return dict(v.split('=',1) for v in r.stdout.splitlines() if '=' in v)

def owner(value):
    require(set(value)=={'pid','birth_ticks','command_sha256'} and type(value['pid']) is int and value['pid']>0,'Incomplete expected owner')
    require(type(value['birth_ticks']) is str and value['birth_ticks'].isdigit() and int(value['birth_ticks'])>0 and str(int(value['birth_ticks']))==value['birth_ticks'],'Canonical owner birth required')
    require(type(value['command_sha256']) is str and len(value['command_sha256'])==64 and all(c in '0123456789abcdef' for c in value['command_sha256']),'Pinned owner command required')
    p=Path('/proc')/str(value['pid'])
    if not p.exists():return None
    return {'pid':value['pid'],'birth_ticks':(p/'stat').read_text().rsplit(')',1)[1].split()[19],'command_sha256':digest((p/'cmdline').read_bytes())}

def same_lifetime(prior):
    current=owner(prior)
    return current is not None and current['birth_ticks']==prior['birth_ticks']

def no_service_processes(name):
    for p in Path('/proc').iterdir():
        if not p.name.isdigit():continue
        try:groups=(p/'cgroup').read_text()
        except (FileNotFoundError,ProcessLookupError):continue
        require(name not in groups,'Service still has a live process')

def pinned(pin,limit=67108864):
    require(set(pin)=={'path','sha256'},'Exact metadata pin required')
    raw=regular(pin['path'],limit);require(digest(raw)==pin['sha256'],'Source closure pin differs');return raw

def source_closure(expected,aura,pins):
    c=expected['source_closure']
    ui=json.loads(regular(aura/'config/board_avatar_gtk.json'));spec=ui['board_business']['face_readback']
    require(c['selected_readback']==spec,'Configured selected readback changed')
    binding=json.loads(pinned(c['selected_readback']))
    require(binding['board_boot_id']==expected['boot_id'] and binding['camera_pid']==expected['camera_owner']['pid'] and str(binding['camera_start_ticks'])==expected['camera_owner']['birth_ticks'] and binding['camera_cmdline_sha256']==expected['camera_owner']['command_sha256'],'Selected camera owner differs')
    verifier=aura/'board/runtime/audio/face_gallery_readback.py';source=regular(verifier)
    require(digest(source)==pins['board/runtime/audio/face_gallery_readback.py']=='b77c32b3863b9464006ac1bb7f16c8f767113925d9142d77e4755f1ce365527e','Unreviewed readback verifier')
    tree=ast.parse(source);klass=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='FaceGalleryReadback')
    method=copy.deepcopy(next(n for n in klass.body if isinstance(n,ast.FunctionDef) and n.name=='_verify'));method.decorator_list=[]
    namespace={'Path':Path,'hashlib':hashlib,'json':json}
    exec(compile(ast.Module(body=[method],type_ignores=[]),str(verifier)+'::<metadata-only-_verify>','exec'),namespace);namespace['_verify'](binding)
    require(binding['camera_config']==c['owner_run_config']['path'] and binding['source_sha256'].get(c['owner_run_config']['path'])==c['owner_run_config']['sha256'],'Current owner run config lacks selected proof')
    run=json.loads(pinned(c['owner_run_config']));native=run['native_execution']
    require(c['native_python_manifest']=={'path':native['source_manifest'],'sha256':native['source_manifest_sha256']},'Run config Python manifest differs')
    manifest=json.loads(pinned(c['native_python_manifest']));native_aura=CHECKPOINT.parent.parent/'aura'
    require(Path(c['native_python_manifest']['path'])==native_aura.parent/'camera-python-manifest.json' and manifest['schema']=='aura-native-python-source-2' and len(manifest['files'])==222,'Original Native Python manifest differs')
    actual={str(p.relative_to(native_aura)):digest(regular(p)) for p in native_aura.rglob('*.py') if not p.is_symlink()}
    require(actual==manifest['files'],'Complete Native Python closure differs')
    require(c['native_operator_manifest']['path']==str(OPERATOR/'runtime-manifest.json'),'Operator manifest path differs')
    operator=json.loads(pinned(c['native_operator_manifest']));require(operator['schema']=='aura-native-operator-runtime-1' and len(operator['files'])==7,'Original operator member set differs')
    for path,sha in operator['files'].items():pinned({'path':path,'sha256':sha})
    require(c['native_c_unit_manifest']=={'path':str(OPERATOR/'source-manifest.json'),'sha256':NATIVE_UNIT},'Original C-unit pin differs')
    unit_manifest=json.loads(pinned(c['native_c_unit_manifest']));require(unit_manifest['schema']=='aura-native-operator-source-unit-1' and unit_manifest['existing_abi']==2 and len(unit_manifest['files'])==6,'Original C-unit shape differs')
    for name,sha in unit_manifest['files'].items():
        relative=Path(name);require(not relative.is_absolute() and '..' not in relative.parts,'C-unit member path escapes')
        pinned({'path':str(OPERATOR/relative),'sha256':sha})
    require(c['native_library']=={'path':str(OPERATOR/'libaura_native_operator.so'),'sha256':NATIVE_LIBRARY},'Original Native library pin differs');pinned(c['native_library'])
    systemd=c['camera_systemd'];r=subprocess.run(['systemctl','show','aura-camera-ui.service','--property=ExecStart,ExecStop,FragmentPath,DropInPaths'],capture_output=True,text=True,timeout=5);require(r.returncode==0,'Camera entry metadata unavailable')
    properties=dict(v.split('=',1) for v in r.stdout.splitlines() if '=' in v)
    require(properties==systemd['properties'],'Camera configured entry changed')
    paths={properties['FragmentPath']}|set(properties['DropInPaths'].split())
    require('' not in paths and paths==set(systemd['source_sha256']),'Camera unit/drop-in source set differs')
    for path,sha in systemd['source_sha256'].items():pinned({'path':path,'sha256':sha})

def get(path):
    c=http.client.HTTPConnection('127.0.0.1',8790,timeout=3)
    try:
        c.request('GET',path);r=c.getresponse();b=r.read(2097153)
        require(r.status==200 and len(b)<=2097152,'Camera metadata request rejected');return json.loads(b)
    finally:c.close()

def create(path,value):
    raw=(json.dumps(value,sort_keys=True,indent=2)+'\n').encode()
    fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
    with os.fdopen(fd,'wb') as f:f.write(raw);f.flush();os.fsync(f.fileno())
    fd=os.open(path.parent,os.O_RDONLY|os.O_DIRECTORY)
    try:os.fsync(fd)
    finally:os.close(fd)

def checked(expected):
    require(expected['schema']=='aura-camera-normal-stop-expected-1' and expected['all_other_writers_frozen'] is True,'Explicit current writer freeze required')
    require(Path('/proc/sys/kernel/random/boot_id').read_text().strip()==expected['boot_id'],'Kernel changed')
    raw=regular(expected['startup']['path']);require(digest(raw)==expected['startup']['sha256'],'Startup changed')
    startup=json.loads(raw);aura=Path(startup['runtime'])/'aura';pins=startup['component_sha256']
    require(len(pins)==380,'Original component closure changed')
    for name,pin in pins.items():require(digest(regular(aura/name))==pin,'Component pin differs')
    gui=unit('aura-avatar-ui.service');camera=unit('aura-camera-ui.service')
    require(all(gui[k]==v for k,v in {'MainPID':'0','ActiveState':'inactive','SubState':'dead','Job':'','Result':'success','ExecMainStatus':'0'}.items()),'GUI has not normally stopped')
    require(expected['stopped_gui_owners'],'Stopped GUI owner evidence required')
    for prior in expected['stopped_gui_owners']:require(not same_lifetime(prior),'Previous GUI owner remains alive')
    no_service_processes('aura-avatar-ui.service')
    require(all(camera[k]==v for k,v in {'MainPID':str(expected['camera_owner']['pid']),'ActiveState':'active','SubState':'running','Job':'','Result':'success','Restart':'no','SendSIGKILL':'no','KillMode':'process','TimeoutStopUSec':'infinity'}.items()),'Original protected camera stop preconditions differ')
    require(owner(expected['camera_owner'])==expected['camera_owner'],'Camera owner changed')
    source_closure(expected,aura,pins)
    require(json.loads(regular('/home/root/.local/share/aura-board-business/listening_preference.json'))=={'version':1,'enabled':False},'Listening preference is not paused')
    health=get('/health');view=get('/v1/ui/status');schedule=health['dpu_schedule'];features=health['identity']['feature_inference']
    require(health['pid']==expected['camera_owner']['pid'] and health['board_boot_id']==expected['boot_id'] and health['motion_command_emitted'] is False,'Camera provenance differs')
    require(health['identity']['ready'] is True and not health['identity'].get('error') and not any(health.get(k) for k in ('camera_error','detector_error','preview_error')),'Camera is not healthy')
    require(schedule['native_critical'] is True and schedule['native_abi']==2 and schedule['owner_fenced'] is False and schedule['quiesced'] is False,'Native owner is not in its original running domain')
    sampling=view['modules']['identity']['enrollment_sampling']
    require(sampling['stage']=='idle','Enrollment sampler is not idle')
    require(all(type(features[k]) is int and features[k]>=0 for k in FEATURES),'Complete current SFace counters required')
    require(type(schedule['primary_calls']) is int and type(schedule['primary_period_overruns']) is int,'Current primary counters required')
    require(set(schedule['optional'])=={'yunet','sface'},'Complete optional task state required')
    for task,optional in schedule['optional'].items():
        require(all(type(optional[k]) is int and optional[k]>=0 for k in ('calls','native_completed','native_failures','not_submitted','overruns')),'Complete current optional counter bounds required')
        recovery=optional['recovery']
        require(all(type(recovery[k]) is int and recovery[k]>=0 for k in ('faults','attempts','recoveries','probe_successes')) and type(recovery['history_opaque']) is bool,'Complete current recovery bounds required')
    require(regular(expected['startup']['path'])==raw and owner(expected['camera_owner'])==expected['camera_owner'],'Owner or startup changed during preflight')
    return raw,schedule,features

def main():
    p=argparse.ArgumentParser();p.add_argument('--expected',type=Path);p.add_argument('--stop',action='store_true');a=p.parse_args()
    expected=globals().get('EXPECTED')
    if expected is None:require(a.expected is not None,'Fresh expected contract required');expected=json.loads(regular(a.expected))
    startup,schedule,features=checked(expected);tx=Path(expected['transaction_directory'])
    require(tx.is_absolute() and tx.parent.resolve(strict=True)==tx.parent and not os.path.lexists(tx),'New nonredirected transaction directory required')
    native_aura=CHECKPOINT.parent.parent/'aura';runtime_aura=Path(json.loads(startup)['runtime'])/'aura'
    for source in (native_aura,runtime_aura):require(source not in tx.parents and tx!=source,'Transaction directory must be outside AURA')
    if not a.stop:
        print(json.dumps({'status':'CURRENT_OWNER_NORMAL_STOP_DRY_RUN_READY','boot_id':expected['boot_id'],'camera_owner':expected['camera_owner'],'startup_sha256':expected['startup']['sha256'],'stop_submitted':False,'files_created':False}));return
    require(os.geteuid()==0,'Expected board root owner required');tx.mkdir(mode=0o700)
    intent={'schema':'aura-original-camera-stop-intent-2','boot_id':expected['boot_id'],'source_owner':expected['camera_owner'],'source_pid':expected['camera_owner']['pid'],'source_birth_ticks':int(expected['camera_owner']['birth_ticks']),'startup':expected['startup'],'stop_intent_mono_ns':time.monotonic_ns(),'primary_calls_lower_bound':schedule['primary_calls'],'primary_period_overruns_lower_bound':schedule['primary_period_overruns'],'prestop_bounds':{'sface':{k:features[k] for k in FEATURES},'optional':schedule['optional']},'all_other_writers_frozen':True,'action':'systemctl stop --no-block aura-camera-ui.service'}
    create(tx/'camera-stop-intent.json',intent)
    require(regular(expected['startup']['path'])==startup and owner(expected['camera_owner'])==expected['camera_owner'],'Fresh stop intent no longer matches current owner')
    r=subprocess.run(['systemctl','stop','--no-block','aura-camera-ui.service'],capture_output=True,text=True,timeout=8);require(r.returncode==0,'Original normal stop submission failed')
    deadline=time.monotonic()+25
    while True:
        state=unit('aura-camera-ui.service');stopped=all(state[k]==v for k,v in {'MainPID':'0','ActiveState':'inactive','SubState':'dead','Job':''}.items())
        if stopped or time.monotonic()>=deadline:break
        time.sleep(.3)
    result={'schema':'aura-original-camera-normal-stop-2','status':'CAMERA_STOPPED' if stopped else 'CAMERA_STOP_PENDING_NO_FORCE','intent':intent,'unit':state,'normal_stop_submitted_once':True,'forced_action':False,'checkpoint_or_marker_written_by_this_script':False,'full_original_validator_still_required':True}
    if stopped:
        require(state['Result']=='success' and state['ExecMainStatus']=='0','Camera normal stop failed')
        require(not same_lifetime(expected['camera_owner']),'Previous camera owner remains alive')
        no_service_processes('aura-camera-ui.service')
        raw=regular(CHECKPOINT,262144);doc=json.loads(raw);seed=doc['seed']
        require(doc['schema']=='aura-native-protection-checkpoint-2' and doc['scope']=='final_quiescent_before_native_owner_close' and seed['purpose']=='final_quiescent_business_checkpoint' and seed['checkpoint_kind']==1,'Exact final checkpoint required')
        require(seed['boot_id']==expected['boot_id'] and seed['source_pid']==expected['camera_owner']['pid'] and seed['source_birth_ticks']==int(expected['camera_owner']['birth_ticks']),'Final source owner differs')
        require(seed['captured_mono_ns']>=intent['stop_intent_mono_ns'] and seed['primary_calls']>=intent['primary_calls_lower_bound'] and seed['primary_period_overruns']>=intent['primary_period_overruns_lower_bound'],'Fresh final violates current-boot observed bounds')
        require(all(doc['auxiliary']['sface_counters'][k]>=features[k] for k in FEATURES),'Fresh final lost current-boot SFace counters')
        require(not os.path.lexists(str(CHECKPOINT)+'.native-consumed-'+digest(raw)) and regular(CHECKPOINT,262144)==raw,'Final changed or was consumed')
        result.update(status='CAMERA_STOPPED_NEW_FINAL_PRESENT',fresh_checkpoint={'path':str(CHECKPOINT),'sha256':digest(raw)},captured_mono_ns=seed['captured_mono_ns'])
    create(tx/'camera-stop-result.json',result);print(json.dumps(result))

if __name__=='__main__':main()
