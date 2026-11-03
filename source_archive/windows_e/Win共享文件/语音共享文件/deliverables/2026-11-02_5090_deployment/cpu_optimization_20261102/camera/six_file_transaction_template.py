"""Root-review template: six stopped-camera files, default dry-run.

No SSH, subprocess, service/model/motion controls, Native imports or checkpoint
writes exist here. Original reader/whole-history semantic validation is an
external root prerequisite, pinned through a normalized receipt. Kernel rename
is atomic; its SHA/inode CAS precondition relies on the explicitly frozen other
writers plus the shared advisory lock. It is not a kernel digest-CAS primitive.
"""
import argparse
import contextlib
import hashlib
import json
import os
from pathlib import Path
import secrets
import stat
import time
import re

UI_ORIGINAL='9d714b9bd00ea1da12088fa1e22100d7bdb689d0cac10332c3933b31e4f4d2df'
UI_V3='7d4773b8ff527773eefc90aa2443dd4bfae801f07c6fcde672af65dd22ff8f66'
NATIVE_UNIT='7cf7eaeecd70e62301d3e12e95d5df6a23bd3e5847ed854200c712598b703c32'
NATIVE_LIBRARY='704f561a50b5f0fb8f9b4cf72c024acce0cdafd888cad0784507f484518fc224'
NAMES=('ui_camera_service.py','camera-python-manifest.json','board_camera_ui.proposed.json',
       'meta.json','native_entry_pan_face_v5.py','runtime-manifest.json')
REFERENCE_SHA={
 'ui_camera_service.py':UI_ORIGINAL,
 'camera-python-manifest.json':'5e08f7cf587d74334ef24104ea01f79701629b48f2004fb772ce3f8ea82afd0d',
 'board_camera_ui.proposed.json':'e137bbb7894ecebcaadc8e57abc4bd8794c80dc3b9c1f87f09389a53ef88af20',
 'native_entry_pan_face_v5.py':'288f6b7b56702edf45b432686db4f77b156408c0b3f78fd31c05edb33df971c4',
 'runtime-manifest.json':'74e011db30a9d943a9512f7648190ac0c01060af06df1280d1e8ea006dc882ad'}

def digest(raw):return hashlib.sha256(raw).hexdigest()
def encode(value):return (json.dumps(value,sort_keys=True,indent=2)+'\n').encode('utf-8')

def regular(path,limit=2000000):
    path=Path(path)
    if not path.is_absolute() or path.resolve()!=path or path.is_symlink():
        raise RuntimeError('Redirected/nonabsolute file path')
    fd=os.open(str(path),os.O_RDONLY|getattr(os,'O_NOFOLLOW',0))
    try:
        info=os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or info.st_size>limit:raise RuntimeError('Not a bounded regular file')
        with os.fdopen(fd,'rb',closefd=False) as stream:value=stream.read(limit+1)
        if len(value)>limit:raise RuntimeError('File exceeds size limit')
        return value,info
    finally:os.close(fd)

def pinned(pin,limit=2000000):
    value,_=regular(pin['path'],limit)
    if digest(value)!=pin['sha256']:raise RuntimeError('Pinned bytes differ')
    return value

def fsync_dir(path):
    fd=os.open(str(path),os.O_RDONLY|getattr(os,'O_DIRECTORY',0))
    try:os.fsync(fd)
    finally:os.close(fd)

def exclusive_file(path,value,mode=0o600,owner=None):
    fd=os.open(str(path),os.O_WRONLY|os.O_CREAT|os.O_EXCL|getattr(os,'O_NOFOLLOW',0),mode)
    try:
        if owner is not None and hasattr(os,'fchown'):os.fchown(fd,*owner)
        if hasattr(os,'fchmod'):os.fchmod(fd,mode)
        else:os.chmod(path,mode)  # Isolated Windows filesystem tests only.
        with os.fdopen(fd,'wb',closefd=False) as stream:
            stream.write(value);stream.flush();os.fsync(stream.fileno())
    finally:os.close(fd)

def token(info):return (info.st_dev,info.st_ino,info.st_size,info.st_mtime_ns,info.st_mode,info.st_uid,info.st_gid)

class SixFileTransaction:
    """Filesystem-only core; tests use isolated temporary public fixtures."""
    def __init__(self,records,backup_dir,guard,after_check,*,fault=None,directory_sync=fsync_dir):
        if len(records)!=6 or tuple(row['name'] for row in records)!=NAMES:
            raise RuntimeError('Exactly the six approved files in fixed order are required')
        self.records=records;self.backup=Path(backup_dir);self.guard=guard
        self.after_check=after_check;self.fault=fault or (lambda *args:None);self.sync=directory_sync
        self.plan=None

    def current(self,allowed):
        values=[]
        for index,row in enumerate(self.records):
            value,info=regular(row['target'])
            if digest(value) not in allowed[index]:raise RuntimeError('Unknown target bytes; no overwrite allowed')
            values.append((value,info))
        return values

    def prepare(self):
        self.guard()
        before=self.current([{row['before_sha256']} for row in self.records])
        payload=[pinned({'path':row['payload'],'sha256':row['after_sha256']}) for row in self.records]
        if self.backup.exists() or self.backup.is_symlink():raise RuntimeError('Backup directory already exists; use explicit recovery')
        self.backup.mkdir(mode=0o700)
        self.sync(self.backup.parent)
        nonce=secrets.token_hex(8);rows=[]
        # Every original and every intended byte is durable before replacement.
        for index,(row,(value,info),after) in enumerate(zip(self.records,before,payload)):
            exclusive_file(self.backup/('before-%02d.bin'%index),value)
            exclusive_file(self.backup/('after-%02d.bin'%index),after)
            rows.append(dict(row,mode=stat.S_IMODE(info.st_mode),uid=info.st_uid,gid=info.st_gid,
                stage=str(Path(row['target']).with_name('.'+Path(row['target']).name+'.aura-'+nonce+'.stage'))))
            self.fault('after_backup',index)
        self.plan={'schema':'aura-six-camera-files-durable-plan-1','files':rows}
        exclusive_file(self.backup/'PLAN.json',encode(self.plan));self.sync(self.backup)
        for index,row in enumerate(rows):
            exclusive_file(row['stage'],payload[index],row['mode'],(row['uid'],row['gid']));self.sync(Path(row['target']).parent)
            self.fault('after_stage',index)
        exclusive_file(self.backup/'PREPARED.json',encode({'all_six_backups_and_payloads_durable':True}))
        self.sync(self.backup)

    def recover_plan(self):
        raw,_=regular(self.backup/'PLAN.json');plan=json.loads(raw)
        if plan.get('schema')!='aura-six-camera-files-durable-plan-1' or len(plan['files'])!=6:
            raise RuntimeError('Recovery plan differs')
        for index,(expected,row) in enumerate(zip(self.records,plan['files'])):
            if any(row.get(k)!=expected.get(k) for k in expected):raise RuntimeError('Recovery plan does not match approved contract')
            target=Path(row['target']);stage=Path(row['stage'])
            if stage.parent!=target.parent or not re.fullmatch(re.escape('.'+target.name+'.aura-')+'[0-9a-f]{16}'+re.escape('.stage'),stage.name):
                raise RuntimeError('Recovery staging path is not the generated same-directory path')
            info=regular(target)[1]
            if (row['mode'],row['uid'],row['gid'])!=(stat.S_IMODE(info.st_mode),info.st_uid,info.st_gid):raise RuntimeError('Target ownership/mode changed')
            for prefix,key in (('before','before_sha256'),('after','after_sha256')):
                pinned({'path':str(self.backup/('%s-%02d.bin'%(prefix,index))),'sha256':row[key]})
            if stage.exists() or stage.is_symlink():pinned({'path':row['stage'],'sha256':row['after_sha256']})
        self.plan=plan

    def commit(self,*,recover=False):
        if recover:self.recover_plan()
        if self.plan is None:raise RuntimeError('Prepare all files first')
        rows=self.plan['files'];self.guard()
        allowed=[{row['before_sha256'],row['after_sha256']} if recover else {row['before_sha256']} for row in rows]
        initial=self.current(allowed);vector=[digest(value) for value,_ in initial]
        attempt=secrets.token_hex(8)
        for index,row in enumerate(rows):
            self.guard()
            current=self.current([{value} for value in vector])
            if vector[index]==row['after_sha256']:continue
            stage=Path(row['stage'])
            if not stage.exists():
                # Recovery may recreate only an absent stage from durable known bytes.
                after=pinned({'path':str(self.backup/('after-%02d.bin'%index)),'sha256':row['after_sha256']})
                exclusive_file(stage,after,row['mode'],(row['uid'],row['gid']));self.sync(stage.parent)
            pinned({'path':str(stage),'sha256':row['after_sha256']})
            exclusive_file(self.backup/('INTENT-'+attempt+'-%02d.json'%index),encode({
                'target':row['target'],'before_sha256':vector[index],'after_sha256':row['after_sha256']}))
            self.sync(self.backup)
            # Check SHA and inode immediately before atomic rename, under the
            # shared exclusive writer freeze/lock. Never repair unknown bytes.
            self.guard()
            value,info=regular(row['target'])
            if digest(value)!=vector[index] or token(info)!=token(current[index][1]):
                raise RuntimeError('Target changed after CAS observation')
            os.replace(str(stage),row['target']);self.sync(Path(row['target']).parent)
            vector[index]=row['after_sha256']
            self.fault('after_replace',index)
            pinned({'path':row['target'],'sha256':row['after_sha256']})
            exclusive_file(self.backup/('DONE-'+attempt+'-%02d.json'%index),encode({'after_sha256':row['after_sha256']}))
            self.sync(self.backup)
        self.current([{row['after_sha256']} for row in rows]);self.guard();self.after_check()
        exclusive_file(self.backup/('COMMITTED-'+attempt+'.json'),encode({'all_six_after_bytes_verified':True}))
        self.sync(self.backup)

def safe_rollback_payload(original_six,fresh_pin):
    """Original code + original manifest + newest fresh seed, never old config verbatim."""
    if tuple(original_six)!=NAMES or digest(original_six['ui_camera_service.py'])!=UI_ORIGINAL:
        raise RuntimeError('Original six-file backup set required')
    if set(fresh_pin)!={'path','sha256'} or not re.fullmatch('[0-9a-f]{64}',fresh_pin['sha256']):
        raise RuntimeError('Complete newest fresh checkpoint pin required')
    config=json.loads(original_six['board_camera_ui.proposed.json'])
    if fresh_pin['path']!=config['native_execution']['checkpoint_output']:
        raise RuntimeError('Rollback checkpoint output differs')
    if fresh_pin==config['native_execution']['seed']:
        raise RuntimeError('Rollback requires the supplied newest fresh pin, not the saved old seed')
    config['native_execution']['seed']=dict(fresh_pin)
    result=dict(original_six);result['board_camera_ui.proposed.json']=encode(config)
    meta=json.loads(original_six['meta.json'])
    if meta['protected'].get(meta['candidate_config'])!=digest(original_six['board_camera_ui.proposed.json']):
        raise RuntimeError('Original meta/config backup relation differs')
    meta['protected'][meta['candidate_config']]=digest(result['board_camera_ui.proposed.json'])
    result['meta.json']=encode(meta)
    return result

def contract_plan_identity(contract):
    """Avoid a self-hash cycle: the root receipt itself is the only omission."""
    return digest(encode({key:value for key,value in contract.items() if key!='root_validation_receipt'}))

def check_known_before(contract,original_six):
    if contract['direction']=='forward':
        if contract['rollback_predecessor_plan'] is not None:raise RuntimeError('First forward reference must be explicit original bytes')
        if any(row['before_sha256']!=digest(original_six[row['name']]) for row in contract['files']):
            raise RuntimeError('Forward before bytes are not the known original six')
    else:
        prior=json.loads(pinned(contract['rollback_predecessor_plan']))
        if prior.get('schema')!='aura-six-camera-files-durable-plan-1' or len(prior.get('files',[]))!=6:
            raise RuntimeError('Rollback requires the pinned prior durable six-file plan')
        for row,old in zip(contract['files'],prior['files']):
            if (row['name']!=old['name'] or row['target']!=old['target']
                    or digest(original_six[row['name']])!=old['before_sha256']
                    or row['before_sha256'] not in (old['before_sha256'],old['after_sha256'])):
                raise RuntimeError('Rollback before bytes are outside the known prior transaction')

def layout(contract):
    required={'schema','direction','camera_root','ops_root','operator_root','backup_dir','files',
        'original_reference','fresh_checkpoint','expected','root_validation_receipt','freeze_guard','coordination_lock','rollback_predecessor_plan'}
    if set(contract)!=required or contract['schema']!='aura-six-camera-file-contract-1':
        raise RuntimeError('Contract schema/fields differ')
    camera=Path(contract['camera_root']);ops=Path(contract['ops_root']);operator=Path(contract['operator_root'])
    if (str(camera)!='/home/root/aura-native-live-20261024/candidates/native-r4-metrics-fix'
            or str(ops)!='/home/root/aura-native-live-20261024/ops/be72669aa53de735'
            or operator!=ops/'pan-face-edge-v5/native-operator-v1'):
        raise RuntimeError('Template is scoped to the approved original project roots')
    for root in (camera,ops,operator):
        if not root.is_absolute() or root.resolve()!=root:raise RuntimeError('Layout path redirects')
    aura=camera/'aura'
    targets=(aura/'board/vision/ui_camera_service.py',camera/'camera-python-manifest.json',
        camera/'board_camera_ui.proposed.json',ops/'meta.json',ops/'native_entry_pan_face_v5.py',operator/'runtime-manifest.json')
    if tuple(row['name'] for row in contract['files'])!=NAMES or tuple(Path(row['target']) for row in contract['files'])!=targets:
        raise RuntimeError('Write set is not the exact six approved paths')
    backup=Path(contract['backup_dir'])
    if not backup.is_absolute() or backup.resolve()!=backup or backup==aura or aura in backup.parents:
        raise RuntimeError('Backups must be outside the Python source closure')
    return camera,ops,operator,aura

def check_source_boundaries(contract):
    """Hash-checked original reference and explicit forward/rollback after graph."""
    camera,ops,operator,aura=layout(contract)
    before={name:pinned(contract['original_reference'][name]) for name in NAMES}
    if any(digest(before[name])!=value for name,value in REFERENCE_SHA.items()):
        raise RuntimeError('Original reference source hashes differ')
    check_known_before(contract,before)
    after={row['name']:pinned({'path':row['payload'],'sha256':row['after_sha256']}) for row in contract['files']}
    direction=contract['direction'];wanted=UI_V3 if direction=='forward' else UI_ORIGINAL
    if direction not in ('forward','rollback') or digest(before['ui_camera_service.py'])!=UI_ORIGINAL or digest(after['ui_camera_service.py'])!=wanted:
        raise RuntimeError('Unreviewed UI source')
    a=json.loads(before['camera-python-manifest.json']);b=json.loads(after['camera-python-manifest.json'])
    expected=json.loads(before['camera-python-manifest.json']);expected['files']['board/vision/ui_camera_service.py']=wanted
    if a.get('schema')!='aura-native-python-source-2' or len(a['files'])!=222 or b!=expected:
        raise RuntimeError('Only one of the original 222 Python members may change')
    old_config=json.loads(before['board_camera_ui.proposed.json']);new_config=json.loads(after['board_camera_ui.proposed.json'])
    expected=json.loads(before['board_camera_ui.proposed.json'])
    expected['native_execution']['source_manifest_sha256']=digest(after['camera-python-manifest.json'])
    expected['native_execution']['seed']=contract['fresh_checkpoint']
    if new_config!=expected or new_config['native_execution']['source_manifest']!=str(camera/'camera-python-manifest.json'):
        raise RuntimeError('Config change exceeds manifest/fresh-seed boundary')
    if new_config['native_execution']['checkpoint_output']!=contract['fresh_checkpoint']['path']:
        raise RuntimeError('Checkpoint output must stay in its original directory')
    if (old_config['native_execution']['source_unit_sha256']!='29786434df9bb9b94a8e640a7a48db47019c224d3876037ce27d3467bb2f5512'
            or old_config['native_execution']['library_sha256']!='c675ba698d45acd8742e52403e6186f43dc56d7d313d0e740896b19412bde656'):
        raise RuntimeError('Original operator predecessor contract differs')
    expected_app=before['native_entry_pan_face_v5.py'].replace(UI_ORIGINAL.encode(),wanted.encode())
    if before['native_entry_pan_face_v5.py'].count(UI_ORIGINAL.encode())!=1 or after['native_entry_pan_face_v5.py']!=expected_app:
        raise RuntimeError('APP source may change only its UI pin')
    expected_meta=json.loads(before['meta.json']);meta=json.loads(after['meta.json'])
    if (expected_meta['candidate_root']!=str(camera)
            or expected_meta['candidate_config']!=str(camera/'board_camera_ui.proposed.json')
            or expected_meta['candidate_ui_sha256']!=UI_ORIGINAL):
        raise RuntimeError('Original meta layout differs')
    for name in ('ui_camera_service.py','camera-python-manifest.json','board_camera_ui.proposed.json'):
        path=next(row['target'] for row in contract['files'] if row['name']==name)
        if expected_meta['protected'].get(path)!=digest(before[name]):raise RuntimeError('Original meta source pins differ')
    expected_meta['candidate_ui_sha256']=wanted
    for name in ('ui_camera_service.py','camera-python-manifest.json','board_camera_ui.proposed.json'):
        path=next(row['target'] for row in contract['files'] if row['name']==name)
        expected_meta['protected'][path]=digest(after[name])
    if meta!=expected_meta:raise RuntimeError('Meta change exceeds UI and three protected pins')
    expected_runtime=json.loads(before['runtime-manifest.json']);runtime=json.loads(after['runtime-manifest.json'])
    if len(expected_runtime['files'])!=7:raise RuntimeError('Original operator seven-file closure required')
    expected_runtime['files'][str(ops/'native_entry_pan_face_v5.py')]=digest(after['native_entry_pan_face_v5.py'])
    if runtime!=expected_runtime or runtime['files'].get(str(operator/'source-manifest.json'))!=NATIVE_UNIT or runtime['files'].get(str(operator/'libaura_native_operator.so'))!=NATIVE_LIBRARY:
        raise RuntimeError('Operator change exceeds APP pin or changes the original C unit/library')
    # All unchanged real members are checked without importing any module.
    actual={str(path.relative_to(aura)):digest(regular(path)[0]) for path in aura.rglob('*.py') if not path.is_symlink()}
    if set(actual)!=set(a['files']):raise RuntimeError('Actual Python source member set differs')
    for name,value in a['files'].items():
        if name!='board/vision/ui_camera_service.py' and actual[name]!=value:raise RuntimeError('Unrelated camera Python member changed')
    for path,value in runtime['files'].items():
        if path!=str(ops/'native_entry_pan_face_v5.py'):pinned({'path':path,'sha256':value})
    return before,after

def live_guard(contract,lock_identity=None):
    """Pinned root attestation plus live read-only boot/owner/marker/native checks."""
    expected=contract['expected'];receipt=json.loads(pinned(contract['root_validation_receipt']))
    if lock_identity is not None:
        lock_raw,lock_info=regular(contract['coordination_lock']['path'])
        if digest(lock_raw)!=contract['coordination_lock']['sha256'] or (lock_info.st_dev,lock_info.st_ino)!=lock_identity:
            raise RuntimeError('The held coordination lock path/inode changed')
    for owner in [expected['stopped_camera_owner']]+expected['stopped_gui_owners']:
        if (type(owner['pid']) is not int or owner['pid']<=0 or int(owner['birth_ticks'])<=0
                or not re.fullmatch('[0-9a-f]{64}',owner['command_sha256'])):
            raise RuntimeError('Incomplete source-owner identity')
    if not expected['stopped_gui_owners']:raise RuntimeError('Stopped GUI source-owner identities required')
    if (receipt.get('schema')!='aura-camera-six-file-root-validation-1'
            or receipt.get('status')!='ORIGINAL_READER_AND_HISTORY_VALIDATED'
            or receipt.get('expected')!=expected or receipt.get('fresh_checkpoint')!=contract['fresh_checkpoint']
            or receipt.get('six_file_plan_sha256')!=contract_plan_identity(contract)
            or receipt.get('normal_camera_stop_confirmed') is not True or receipt.get('gui_stopped_confirmed') is not True
            or receipt.get('all_other_writers_frozen') is not True):raise RuntimeError('Root validation/freeze attestation differs')
    pinned(receipt['original_reader_receipt'])
    pinned(contract['freeze_guard'])
    if Path('/proc/sys/kernel/random/boot_id').read_text().strip()!=expected['boot_id']:raise RuntimeError('Kernel boot changed')
    age=time.monotonic_ns()-receipt['observed_mono_ns']
    if not 0<=age<=min(expected['max_receipt_age_ms'],60000)*1000000:raise RuntimeError('Root receipt is stale')
    for owner in [expected['stopped_camera_owner']]+expected['stopped_gui_owners']:
        path=Path('/proc')/str(owner['pid'])/'stat'
        if path.exists() and int(path.read_text().rsplit(')',1)[1].split()[19])==int(owner['birth_ticks']):
            raise RuntimeError('A stopped source owner is still alive')
    for process in Path('/proc').iterdir():
        if not process.name.isdigit():continue
        try:
            cgroup=(process/'cgroup').read_text();maps=(process/'maps').read_text()
        except (FileNotFoundError,ProcessLookupError):continue
        if 'aura-camera-ui.service' in cgroup or 'aura-avatar-ui.service' in cgroup:
            raise RuntimeError('Camera/GUI service still has a process')
        if 'libaura_native_operator.so' in maps or 'libaura_native_v2_candidate.so' in maps:
            raise RuntimeError('An unknown Native owner remains mapped')
    raw=pinned(contract['fresh_checkpoint'],262144);document=json.loads(raw);seed=document['seed']
    owner=expected['stopped_camera_owner'];pin=contract['fresh_checkpoint']
    if (document.get('schema')!='aura-native-protection-checkpoint-2'
            or document.get('scope')!='final_quiescent_before_native_owner_close'
            or seed['boot_id']!=expected['boot_id'] or seed['source_pid']!=owner['pid']
            or int(seed['source_birth_ticks'])!=int(owner['birth_ticks']) or document['source_unit_sha256']!=NATIVE_UNIT):
        raise RuntimeError('Fresh final does not belong to the current stopped owner/C unit')
    marker=Path(pin['path']+'.native-consumed-'+pin['sha256'])
    if marker.exists() or marker.is_symlink():raise RuntimeError('Fresh final has already been consumed')
    operator=Path(contract['operator_root']);unit=json.loads(pinned({'path':str(operator/'source-manifest.json'),'sha256':NATIVE_UNIT}))
    if unit.get('schema')!='aura-native-operator-source-unit-1' or unit.get('existing_abi')!=2 or len(unit['files'])!=6:
        raise RuntimeError('Original six-file Native unit differs')
    for name,value in unit['files'].items():pinned({'path':str(operator/name),'sha256':value})
    pinned({'path':str(operator/'libaura_native_operator.so'),'sha256':NATIVE_LIBRARY})

@contextlib.contextmanager
def writer_lock(contract):
    import fcntl
    pin=contract['coordination_lock'];pinned(pin)
    fd=os.open(pin['path'],os.O_RDONLY|os.O_NOFOLLOW)
    try:
        fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
        raw,current=regular(pin['path']);held=os.fstat(fd)
        if digest(raw)!=pin['sha256'] or (current.st_dev,current.st_ino)!=(held.st_dev,held.st_ino):
            raise RuntimeError('Coordination lock bytes/inode changed')
        yield (held.st_dev,held.st_ino)
    finally:os.close(fd)

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--contract',type=Path,required=True)
    parser.add_argument('--apply',action='store_true')
    parser.add_argument('--recover',action='store_true',help='Check/finish only known after-bytes; still dry-run unless --apply')
    args=parser.parse_args()
    if os.name!='posix' or not hasattr(os,'O_NOFOLLOW') or os.geteuid()!=0:raise RuntimeError('Actual executor requires target POSIX root')
    contract=json.loads(regular(args.contract.resolve())[0]);layout(contract)
    with writer_lock(contract) as held_lock:
        live_guard(contract,held_lock);check_source_boundaries(contract)
        records=contract['files']
        def after_check():
            for row in records:pinned({'path':row['target'],'sha256':row['after_sha256']})
            check_source_boundaries(contract)
        tx=SixFileTransaction(records,contract['backup_dir'],lambda:live_guard(contract,held_lock),after_check)
        if not args.apply:
            if args.recover:tx.recover_plan()
            tx.current([{row['before_sha256'],row['after_sha256']} if args.recover else {row['before_sha256']} for row in records])
            print(json.dumps({'status':'DRY_RUN_RECOVERY_VALIDATED' if args.recover else 'DRY_RUN_VALIDATED','target_files_written':False}));return
        if not args.recover:tx.prepare()
        tx.commit(recover=args.recover)
        print(json.dumps({'status':'SIX_FILES_COMMITTED_SERVICES_STILL_STOPPED','backup_dir':contract['backup_dir']}))

if __name__=='__main__':main()
