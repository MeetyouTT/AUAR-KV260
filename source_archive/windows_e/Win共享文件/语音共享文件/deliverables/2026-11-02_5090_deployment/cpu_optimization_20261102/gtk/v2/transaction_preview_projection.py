"""ROOT-REVIEW TEMPLATE. Defaults to dry-run. No service or motion controls.

Provide a fresh EXPECTED dict and PAYLOAD_BASE64 via a trusted stdin prefix,
or use --expected/--payload files. --apply is the sole mutation switch.
This script is not a substitute for the root's current writer freeze/handover.
"""
import argparse
import base64
import copy
import datetime
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import subprocess

TARGETS=('board/interaction/ui_services.py','tools/board_camera_preview.py')
OLD={'board/interaction/ui_services.py':'b55ee295e2cb5494f387fbaa4aa081fd1d6bffd57588c018c5f31daae56bd711',
     'tools/board_camera_preview.py':'6e697c16f7ae264dff56b6b35f38da4b531ea13026b69a7c8bdbfb1960a6afcd'}
NEW={'board/interaction/ui_services.py':'e4dedf9b3d56d22d9eb93de1e96ad1a69870d553ea50f7dd5082b21e19f381c9',
     'tools/board_camera_preview.py':'67d6c0f2b24ea97e20fdcc7b3383b6444269a6e26f5deb566f2b88746b7daf9b'}
CONTRACT='7f67e4bdfe4a95396fbe6445759c80f8ea79cf51d2d991269213409a83daec86'
MAX_BYTES=64*1024*1024

class Hold(RuntimeError):pass
def require(value,reason):
    if not value:raise Hold(reason)
def sha(data):return hashlib.sha256(data).hexdigest()
def sha_value(value):return type(value) is str and re.fullmatch('[0-9a-f]{64}',value) is not None
def fingerprint(info):return (info.st_dev,info.st_ino,info.st_size,info.st_mtime_ns,stat.S_IMODE(info.st_mode),info.st_uid,info.st_gid)
def read_file(path):
    path=Path(path)
    require(path.is_absolute() and not path.is_symlink(),'HOLD_NONABSOLUTE_OR_SYMLINK_FILE')
    require(path.suffix.lower() not in ('.db','.sqlite','.sqlite3','.wav','.pcm','.key'),'HOLD_PRIVATE_OR_NON_SOURCE_FILE')
    fd=os.open(str(path),os.O_RDONLY|os.O_NOFOLLOW)
    with os.fdopen(fd,'rb') as stream:
        before=os.fstat(stream.fileno())
        require(stat.S_ISREG(before.st_mode) and before.st_size<=MAX_BYTES,'HOLD_SOURCE_FILE_TYPE_OR_SIZE')
        data=stream.read(MAX_BYTES+1);after=os.fstat(stream.fileno())
    require(len(data)<=MAX_BYTES and fingerprint(before)==fingerprint(after)==fingerprint(path.stat()),'HOLD_FILE_CHANGED_DURING_READ')
    return data,fingerprint(after)
def pinned(path,digest):
    require(sha_value(digest),'HOLD_BAD_SHA_INPUT')
    data,identity=read_file(path);require(sha(data)==digest,'HOLD_PIN_MISMATCH:'+str(path))
    return data,identity
def fsync_dir(path):
    fd=os.open(str(path),os.O_RDONLY|os.O_DIRECTORY)
    try:os.fsync(fd)
    finally:os.close(fd)
def create(path,data,mode=0o600):
    path=Path(path);require(path.parent.is_dir() and not path.parent.is_symlink(),'HOLD_BAD_CREATE_PARENT')
    fd=os.open(str(path),os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,mode)
    with os.fdopen(fd,'wb') as stream:
        stream.write(data);stream.flush();os.fsync(stream.fileno())
    fsync_dir(path.parent)
def json_bytes(value):return (json.dumps(value,ensure_ascii=False,indent=2,allow_nan=False)+'\n').encode('utf-8')
def proc(pid):
    require(type(pid) is int and pid>0,'HOLD_BAD_PID')
    root=Path('/proc')/str(pid)
    try:
        ticks=(root/'stat').read_text().rsplit(')',1)[1].split()[19]
        return {'pid':pid,'birth_ticks':ticks,'command_sha256':sha((root/'cmdline').read_bytes())}
    except (FileNotFoundError,ProcessLookupError):return None
def owner(value):
    require(set(value)=={'pid','birth_ticks','command_sha256'} and type(value['birth_ticks']) is str and value['birth_ticks'].isdigit() and sha_value(value['command_sha256']),'HOLD_OWNER_INPUT')
    return value
def show(name):
    result=subprocess.run(['systemctl','show',name,'--property=MainPID,ActiveState,SubState,Job,Result,ExecMainStatus'],capture_output=True,text=True,timeout=5)
    require(result.returncode==0,'HOLD_UNIT_METADATA_UNAVAILABLE')
    return dict(row.split('=',1) for row in result.stdout.splitlines() if '=' in row)
def guards(expected):
    require(Path('/proc/sys/kernel/random/boot_id').read_text().strip()==expected['boot_id'],'HOLD_BOOT_CHANGED')
    gui=show('aura-avatar-ui.service')
    require(gui=={'MainPID':'0','ActiveState':'inactive','SubState':'dead','Job':'','Result':'success','ExecMainStatus':'0'},'HOLD_GUI_NOT_NORMALLY_STOPPED')
    owners=expected['owners'];require(set(owners)=={'camera','gui_supervisor','gui_gtk'},'HOLD_OWNER_SET')
    camera=owner(owners['camera']);require(proc(camera['pid'])==camera,'HOLD_CAMERA_OWNER_CHANGED')
    camera_unit=show('aura-camera-ui.service')
    require(camera_unit['MainPID']==str(camera['pid']) and camera_unit['ActiveState']=='active' and camera_unit['SubState']=='running' and camera_unit['Job']=='' and camera_unit['Result']=='success','HOLD_CAMERA_NOT_RUNNING')
    for key in ('gui_supervisor','gui_gtk'):
        previous=owner(owners[key]);require(proc(previous['pid'])!=previous,'HOLD_PREVIOUS_GUI_OWNER_STILL_ALIVE')

def validate_rel(name):
    value=Path(name)
    require(type(name) is str and not value.is_absolute() and '..' not in value.parts,'HOLD_COMPONENT_PATH')
    return value

def selected_readback(aura,startup,targets):
    ui=json.loads(read_file(aura/'config/board_avatar_gtk.json')[0])
    spec=ui['board_business']['face_readback'];path=Path(spec['path'])
    raw,identity=pinned(path,spec['sha256']);binding=json.loads(raw)
    sources=binding['source_sha256'];require(isinstance(sources,dict) and 1<=len(sources)<=512,'HOLD_SELECTED_SOURCE_MAP')
    hits=[name for name in sources if Path(name).resolve()==targets.get(str(Path(name).resolve()))]
    require(not hits,'HOLD_SELECTED_READBACK_PINS_MODIFIED_COMPONENT:'+','.join(hits))
    ids={str(path):identity}
    for name,digest in sources.items():
        source=Path(name);require(source.is_absolute(),'HOLD_SELECTED_RELATIVE_SOURCE')
        data,source_identity=pinned(source,digest);ids[str(source)]=source_identity
    return {'path':str(path),'sha256':spec['sha256'],'source_count':len(sources),'ids':ids,'binding':binding}

def pan_closure(aura,component_pins):
    component_names=sorted(name for name in component_pins if name.startswith('config/pan_'))
    require(component_names and 'config/pan_face.local.json' in component_names,'HOLD_PAN_COMPONENT_SET')
    face=json.loads(read_file(aura/'config/pan_face.local.json')[0])
    release=Path(face['release_root']);require(release.is_absolute() and not release.is_symlink(),'HOLD_PAN_ROOT')
    manifest_path=release/'deployment-manifest.json'
    raw,_=pinned(manifest_path,face['manifest_sha256']);manifest=json.loads(raw)
    files=manifest['files'];require(isinstance(files,list) and len(files)==25,'HOLD_PAN_25_FILE_MANIFEST')
    external={str(manifest_path):sha(raw)}
    for row in files:
        path=Path(row['destination']);require(path.is_absolute(),'HOLD_PAN_MANIFEST_DESTINATION')
        try:path.resolve().relative_to(release.resolve())
        except ValueError:raise Hold('HOLD_PAN_MANIFEST_DESTINATION')
        require(str(path) not in external and sha_value(row['sha256']),'HOLD_PAN_MANIFEST_DUPLICATE_OR_SHA')
        external[str(path)]=row['sha256']
    for key in ('context','direction-evidence','human-evidence','manifest','zone-settings'):
        path=Path(face.get('arguments',{}).get(key,''));require(path.is_absolute(),'HOLD_PAN_ARGUMENT_SOURCE:'+key)
        external.setdefault(str(path),sha(read_file(path)[0]))
    manual=json.loads(read_file(aura/'config/pan_manual.local.json')[0])
    if manual.get('release_manifest'):
        path=Path(manual['release_manifest']);external[str(path)]=manual['release_manifest_sha256']
    return {name:component_pins[name] for name in component_names},external

def check_closure(context,overrides=None,startup_bytes=None,first=False):
    expected=context['expected'];aura=context['aura'];guards(expected)
    actual,identity=read_file(context['startup_path'])
    require(actual==(startup_bytes if startup_bytes is not None else context['startup_raw']),'HOLD_STARTUP_CAS')
    if not first:require(identity==context['identities'][str(context['startup_path'])],'HOLD_STARTUP_IDENTITY_CHANGED')
    overrides=overrides or {}
    for name,digest in context['pins'].items():
        path=aura/validate_rel(name);raw,file_id=pinned(path,overrides.get(name,digest))
        key=str(path)
        if first:context['identities'][key]=file_id
        else:require(file_id==context['identities'][key],'HOLD_COMPONENT_CONCURRENT_CHANGE:'+name)
    for path,digest in expected['pan_external_sha256'].items():
        raw,file_id=pinned(Path(path),digest)
        if first:context['identities'][path]=file_id
        else:require(file_id==context['identities'][path],'HOLD_PAN_CONCURRENT_CHANGE:'+path)
    mutated=[aura/name for name in TARGETS]+[context['startup_path']]
    binding=selected_readback(aura,context['startup'],{str(path.resolve()):path.resolve() for path in mutated})
    require(binding['sha256']==expected['selected_readback_sha256'],'HOLD_SELECTED_BINDING_CHANGED')
    require(type(expected['selected_readback_source_count']) is int and 1<=expected['selected_readback_source_count']<=512 and binding['source_count']==expected['selected_readback_source_count'],'HOLD_SELECTED_SOURCE_COUNT_CHANGED')
    camera=expected['owners']['camera']
    require(binding['binding']['board_boot_id']==expected['boot_id'] and binding['binding']['camera_pid']==camera['pid'] and str(binding['binding']['camera_start_ticks'])==camera['birth_ticks'] and binding['binding']['camera_cmdline_sha256']==camera['command_sha256'],'HOLD_SELECTED_CAMERA_BINDING')
    for path,file_id in binding['ids'].items():
        if first:context['identities'][path]=file_id
        else:require(file_id==context['identities'][path],'HOLD_SELECTED_SOURCE_CONCURRENT_CHANGE')

def startup_after(current,target_pins):
    result=copy.deepcopy(current)
    require(len(result['component_sha256'])==380,'HOLD_COMPONENT_COUNT')
    for name,digest in target_pins.items():result['component_sha256'][name]=digest
    before=copy.deepcopy(current);after=copy.deepcopy(result)
    for name in TARGETS:before['component_sha256'].pop(name);after['component_sha256'].pop(name)
    require(before==after,'HOLD_UNRELATED_STARTUP_CHANGE')
    return json_bytes(result)

def preflight(expected,payload,action,tx):
    require(expected.get('maintenance_writers_frozen') is True,'HOLD_NO_CURRENT_WRITER_FREEZE')
    require(sha_value(expected['startup_sha256']),'HOLD_STARTUP_SHA_INPUT')
    startup_path=Path(expected['startup_path']);raw,identity=pinned(startup_path,expected['startup_sha256'])
    startup=json.loads(raw);aura=Path(startup['runtime'])/'aura'
    require(aura.is_absolute() and aura.is_dir() and not aura.is_symlink(),'HOLD_RUNTIME_ROOT')
    pins=startup['component_sha256'];require(len(pins)==380,'HOLD_COMPONENT_COUNT')
    require(set(payload['components'])==set(TARGETS),'HOLD_PAYLOAD_COMPONENT_SET')
    expected_sources=expected['source_sha256'];require(set(TARGETS)|{'board/interaction/ui_contract.py'}<=set(expected_sources),'HOLD_FRESH_SOURCE_PINS_MISSING')
    for name,digest in expected_sources.items():
        require(name in pins and sha_value(digest),'HOLD_EXPECTED_SOURCE_PIN')
        if name not in TARGETS:require(pins[name]==digest,'HOLD_UNRELATED_EXPECTED_SOURCE_PIN')
    require(expected_sources['board/interaction/ui_contract.py']==pins['board/interaction/ui_contract.py']==CONTRACT,'HOLD_UNREVIEWED_GATE_SOURCE')
    current_targets={}
    for name in TARGETS:
        require(payload['components'][name]['old_sha256']==OLD[name] and payload['components'][name]['new_sha256']==NEW[name],'HOLD_PAYLOAD_PIN')
        candidate=base64.b64decode(payload['components'][name]['new_bytes_base64'],validate=True)
        require(sha(candidate)==NEW[name],'HOLD_PAYLOAD_BYTES')
        actual=sha(read_file(aura/name)[0]);require(actual==expected_sources[name],'HOLD_SOURCE_CAS')
        if action=='install':require(actual==pins[name]==OLD[name],'HOLD_INSTALL_SOURCE_NOT_ORIGINAL')
        else:require(actual in (OLD[name],NEW[name]) and pins[name] in (OLD[name],NEW[name]),'HOLD_ROLLBACK_UNKNOWN_TARGET')
        current_targets[name]=actual
    actual_pan,external=pan_closure(aura,pins)
    require(actual_pan==expected['pan_component_sha256'],'HOLD_PAN_COMPONENT_INPUT_CHANGED')
    require(external==expected['pan_external_sha256'],'HOLD_PAN_EXTERNAL_INPUT_CHANGED')
    require(not set(external)&({str(aura/name) for name in TARGETS}|{str(startup_path)}),'HOLD_PAN_SOURCE_OVERLAPS_MUTATION_TARGET')
    tx_root=Path(expected['transaction_root'])
    require(tx_root.is_absolute() and tx_root.is_dir() and not tx_root.is_symlink(),'HOLD_TRANSACTION_ROOT')
    require(tx.is_absolute() and tx.parent.resolve()==tx_root.resolve() and re.fullmatch('[A-Za-z0-9][A-Za-z0-9._-]{0,95}',tx.name),'HOLD_TRANSACTION_PATH')
    context={'expected':expected,'startup_path':startup_path,'startup_raw':raw,'startup':startup,'aura':aura,'pins':pins,
        'current_targets':current_targets,'identities':{str(startup_path):identity},'tx_root':tx_root,'tx':tx}
    check_closure(context,overrides=current_targets,first=True)
    return context

def make_dirs(root,relative):
    path=root
    for part in Path(relative).parts:
        require(part not in ('..','.'),'HOLD_BACKUP_PATH')
        path=path/part
        if not path.exists():os.mkdir(path,0o700);fsync_dir(path.parent)
        require(path.is_dir() and not path.is_symlink(),'HOLD_BACKUP_DIRECTORY')
    return path

def replace_target(context,path,before,new,attempt):
    raw,identity=read_file(path);require(raw==before and identity==context['identities'][str(path)],'HOLD_TARGET_CAS')
    stage=path.parent/('.aura-ui-cpu-'+attempt+'-'+path.name+'.stage')
    create(stage,new,identity[4])
    os.chown(stage,identity[5],identity[6]);fd=os.open(str(stage),os.O_RDONLY|os.O_NOFOLLOW)
    try:
        os.fchmod(fd,identity[4])
        os.fsync(fd)
    finally:os.close(fd)
    staged,stage_id=read_file(stage)
    require(staged==new and stage_id[4:7]==identity[4:7],'HOLD_STAGE_BYTES_OR_OWNERSHIP_MODE')
    # Root's writer freeze + cooperative lock is required throughout this CAS.
    again,file_id=read_file(path);require(again==before and file_id==identity,'HOLD_TARGET_CHANGED_AFTER_STAGE')
    os.replace(stage,path);fsync_dir(path.parent)
    actual,now=read_file(path)
    require(actual==new and now[4:7]==identity[4:7],'HOLD_TARGET_BYTES_OR_OWNERSHIP_MODE_AFTER_REPLACE')
    context['identities'][str(path)]=now

def execute(context,payload,action,apply,rollback_id):
    tx=context['tx'];expected=context['expected'];aura=context['aura']
    if action=='install':
        require(not tx.exists(),'HOLD_TRANSACTION_ALREADY_EXISTS')
        destination={name:base64.b64decode(payload['components'][name]['new_bytes_base64'],validate=True) for name in TARGETS}
        desired=NEW;attempt=tx.name;work=tx
    else:
        require(tx.is_dir() and not tx.is_symlink(),'HOLD_ROLLBACK_TRANSACTION_MISSING')
        plan=json.loads(read_file(tx/'plan.json')[0])
        require(plan['action']=='install' and plan['original_sha256']==OLD and plan['candidate_sha256']==NEW,'HOLD_ROLLBACK_PLAN')
        destination={name:pinned(tx/'backup'/name,OLD[name])[0] for name in TARGETS}
        require(re.fullmatch('[A-Za-z0-9][A-Za-z0-9._-]{0,63}',rollback_id or ''),'HOLD_ROLLBACK_ID_REQUIRED')
        attempt=tx.name+'-rollback-'+rollback_id;work=tx/('rollback-'+rollback_id)
        require(not work.exists(),'HOLD_ROLLBACK_ATTEMPT_ALREADY_EXISTS');desired=OLD
    new_startup=startup_after(context['startup'],desired)
    report={'status':'DRY_RUN_READY','action':action,'apply':apply,'boot_id':expected['boot_id'],
        'components_verified':380,'selected_readback_sha256':expected['selected_readback_sha256'],
        'selected_readback_source_count':expected['selected_readback_source_count'],
        'preflight_component_pins_match':all(context['current_targets'][name]==context['pins'][name] for name in TARGETS),
        'pan_component_pins_preserved':expected['pan_component_sha256'],
        'pan_external_file_count':len(expected['pan_external_sha256']),
        'startup_before_sha256':sha(context['startup_raw']),'startup_after_sha256':sha(new_startup),
        'runtime_mutation_targets':[str(aura/name) for name in TARGETS]+[str(context['startup_path'])],
        'transaction_directory':str(work),'services_or_models_or_camera_or_axis_controlled':False}
    if not apply:return report
    require(os.geteuid()==0,'HOLD_APPLY_REQUIRES_EXPECTED_BOARD_ROOT_OWNER')
    lock_path=context['startup_path'].parent/'.gtk-preview-cpu-deploy.lock'
    descriptor=os.open(str(lock_path),os.O_RDWR|os.O_CREAT|os.O_NOFOLLOW|os.O_NONBLOCK,0o600)
    locked=False
    try:
        info=os.fstat(descriptor)
        require(stat.S_ISREG(info.st_mode) and info.st_uid==0,'HOLD_COOPERATIVE_LOCK_FILE_TYPE')
        try:fcntl.flock(descriptor,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:raise Hold('HOLD_COOPERATIVE_DEPLOY_LOCK_BUSY')
        locked=True
        check_closure(context,context['current_targets'])
        os.mkdir(work,0o700);fsync_dir(work.parent)
        plan=dict(report,original_sha256=OLD,candidate_sha256=NEW,
            source_before_sha256=context['current_targets'],payload_sha256=payload['_verified_payload_sha256'],
            expected=expected,created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat())
        create(work/'intent.json',json_bytes({'action':action,'status':'PREPARING','plan_startup_sha256':sha(context['startup_raw']),
            'target_components':list(TARGETS),'payload_sha256':payload['_verified_payload_sha256']}))
        os.mkdir(work/'backup',0o700);fsync_dir(work)
        for name in TARGETS:
            make_dirs(work/'backup',Path(name).parent)
            create(work/'backup'/name,pinned(aura/name,context['current_targets'][name])[0])
        create(work/'backup/startup.before.json',context['startup_raw'])
        create(work/'startup.after.json',new_startup)
        create(work/'plan.json',json_bytes(plan))
        active=dict(context['current_targets'])
        for name in TARGETS:
            check_closure(context,active)
            path=aura/name;before=pinned(path,active[name])[0]
            if before!=destination[name]:replace_target(context,path,before,destination[name],attempt)
            active[name]=desired[name]
        check_closure(context,active)
        replace_target(context,context['startup_path'],context['startup_raw'],new_startup,attempt)
        check_closure(context,active,startup_bytes=new_startup)
        report.update(status='COMMITTED',committed=True,post_commit_component_pins_match=True)
        create(work/'receipt.json',json_bytes(report))
        return report
    finally:
        if locked:fcntl.flock(descriptor,fcntl.LOCK_UN)
        os.close(descriptor)

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--expected',type=Path)
    parser.add_argument('--payload',type=Path)
    parser.add_argument('--payload-sha256',required=True)
    parser.add_argument('--transaction',type=Path,required=True)
    parser.add_argument('--action',choices=('install','rollback'),default='install')
    parser.add_argument('--rollback-id')
    parser.add_argument('--apply',action='store_true')
    args=parser.parse_args()
    require(sha_value(args.payload_sha256),'HOLD_PAYLOAD_SHA_INPUT')
    expected=globals().get('EXPECTED')
    if expected is None:require(args.expected is not None,'HOLD_FRESH_EXPECTED_INPUT_REQUIRED');expected=json.loads(read_file(args.expected)[0])
    require(type(expected) is dict,'HOLD_EXPECTED_TYPE')
    payload_b64=globals().get('PAYLOAD_BASE64')
    if payload_b64 is None:require(args.payload is not None,'HOLD_PAYLOAD_REQUIRED');raw=read_file(args.payload)[0]
    else:raw=base64.b64decode(payload_b64,validate=True)
    require(sha(raw)==args.payload_sha256,'HOLD_PAYLOAD_DIGEST')
    payload=json.loads(raw);require(payload['schema']=='aura-ui-preview-projection-payload-1','HOLD_PAYLOAD_SCHEMA')
    payload['_verified_payload_sha256']=sha(raw)
    context=preflight(expected,payload,args.action,args.transaction)
    print(json.dumps(execute(context,payload,args.action,args.apply,args.rollback_id),sort_keys=True))

if __name__=='__main__':
    try:main()
    except Hold as exc:
        print(json.dumps({'status':'HOLD','reason':str(exc),'automatic_retry':False,'automatic_rollback':False}));raise SystemExit(2)
    except (OSError,ValueError,KeyError,TypeError,subprocess.SubprocessError) as exc:
        print(json.dumps({'status':'HOLD_IO_OR_INPUT_OR_PARTIAL_RESULT','reason_type':type(exc).__name__,
            'automatic_retry':False,'automatic_rollback':False}));raise SystemExit(3)
