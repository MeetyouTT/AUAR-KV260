"""Root-only formal character publisher. Default inspect has no mutation.

Explicit one-action CLI; no TERM/kill/systemctl stop/restart. Old and new GTK
exit through exact-window WM_DELETE. All existing business/HOME/settings stay.
"""
import argparse
import copy
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import subprocess
import time
import zipfile

UNIT='aura-avatar-ui.service'
PREFIX='/home/root/aura-character-xuefei-20261030/'
LAUNCHER_SHA='5b15a8cf1813935679e5f4d30eb788e9c8d6ae18826669009d06c92cba152e03'
PROMPT='11b1b4d04c55ac110969fd5dd7ffb37f29b29bbc26d9c7906e454d4f69af654e'
PAIR='xuefei-yuki-board-v1-candidate'


def need(value,code):
    if not value:raise ValueError(code)
def sha(raw):return hashlib.sha256(raw).hexdigest()
def encoded(value):return (json.dumps(value,ensure_ascii=False,sort_keys=True,indent=2)+'\n').encode()
def parse(raw):
    def unique(pairs):
        value={}
        for k,v in pairs:need(k not in value,'duplicate_json_key');value[k]=v
        return value
    return json.loads(raw,object_pairs_hook=unique,parse_constant=lambda _:(_ for _ in ()).throw(ValueError('nonfinite_json')))
def relative(value):
    p=PurePosixPath(value)
    need(isinstance(value,str) and value and not p.is_absolute() and '..' not in p.parts
         and str(p)==value and '\\' not in value,'relative_path_required')
    return value
def read(path,expected=None,maximum=16777216,aliases=None):
    path=Path(path);row=(aliases or {}).get(str(path));resolved=path.resolve(strict=True)
    if row:
        need(str(resolved)==row['resolved'] and path.is_symlink()==row['symlink']
             and row['sha256']==expected,'reviewed_alias_changed')
    else:need(resolved==path and not path.is_symlink(),'canonical_file_required')
    need(resolved.resolve(strict=True)==resolved and resolved.is_file() and not resolved.is_symlink()
         and resolved.stat().st_size<=maximum,'bounded_regular_file_required')
    raw=path.read_bytes();need(len(raw)<=maximum,'file_size_changed')
    if expected:need(sha(raw)==expected,'file_sha_changed')
    if row:need(len(raw)==row['bytes'] and resolved.read_bytes()==raw and path.resolve(strict=True)==resolved,'alias_bytes_changed')
    return raw
def command(argv,timeout=8):
    r=subprocess.run(argv,stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,
                     text=True,timeout=timeout,check=False)
    need(r.returncode==0 and len(r.stdout)<=2097152,'bounded_command_failed')
    return r.stdout
def show():
    return dict(x.split('=',1) for x in command(['/bin/systemctl','show',UNIT,'--no-pager',
        '--property=MainPID,ActiveState,SubState,Job,ExecStart,DropInPaths,Restart,SendSIGKILL,TimeoutStopUSec,TimeoutStartUSec,UnitFileState']).splitlines() if '=' in x)
def process(pid):
    try:
        p=Path('/proc')/str(pid);fields=(p/'stat').read_text().rsplit(')',1)[1].split();raw=(p/'cmdline').read_bytes()
    except FileNotFoundError:return None
    if not raw or fields[0]=='Z':return None
    need(len(raw)<=1048576 and raw.endswith(b'\0'),'proc_command_invalid')
    return dict(pid=pid,birth=fields[19],cmdline_sha256=sha(raw),argv=[v.decode() for v in raw.split(b'\0') if v],ppid=int(fields[1]))
def same(actual,expected):return bool(actual and all(actual.get(k)==expected.get(k) for k in ('pid','birth','cmdline_sha256')))
def exec_argv(value):
    m=re.search(r'argv\[\]=([^;]+);',value);need(m,'unit_exec_argv_required');return m.group(1).strip()
def create(path,raw,mode=0o600):
    path=Path(path);need(path.parent.resolve(strict=True)==path.parent and not path.is_symlink(),'canonical_output_parent_required')
    fd=os.open(str(path),os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,mode)
    with os.fdopen(fd,'wb') as out:out.write(raw);out.flush();os.fsync(out.fileno())
def save(p,value):
    path=Path(p['control'])/'state.json';tmp=path.with_name('state.tmp-'+str(os.getpid()))
    create(tmp,encoded(value));os.replace(str(tmp),str(path))
    fd=os.open(str(path.parent),os.O_RDONLY|os.O_DIRECTORY)
    try:os.fsync(fd)
    finally:os.close(fd)
def journal(p):return parse(read(p['control']+'/state.json'))
def checks(p):
    need(p['schema']==1 and p['target'].startswith(PREFIX) and p['control'].startswith(PREFIX)
         and '..' not in PurePosixPath(p['target']).parts and '..' not in PurePosixPath(p['control']).parts
         and p['target']!=p['control'],'formal_namespace_required')
    need(Path('/proc/sys/kernel/random/boot_id').read_text().strip()==p['boot_id'],'boot_changed')
    need(same(process(p['camera']['pid']),p['camera']),'camera_owner_changed')
    o=p['original'];need(o['launcher_sha256']==LAUNCHER_SHA and len(o['pins'])==286,'original_r3_required')
    startup=parse(read(o['startup'],o['startup_sha256']))
    need(startup['runtime']==o['runtime'] and startup['component_sha256']==o['pins'],'original_startup_changed')
    read(o['launcher'],LAUNCHER_SHA)
    for path,expected in o['unit_sources'].items():read(path,expected)
    return startup
def state(p):
    # Reuse only the frozen probe's bounded GET implementation, not run/main.
    module=load_module(p['public_probe'],p['public_probe_sha256'],'_formal_readonly_state')
    v=module._local_json(8783,'/api/state');h=v.get('handsfree_dialogue',{});pan=v.get('manual_pan',{})
    need(v.get('phase')=='IDLE' and v.get('playing') is False and h.get('enabled') is False
         and h.get('microphone_open') is False and pan.get('automatic_following') is False
         and pan.get('state')=='FAULT' and 'pulse_us' in pan and pan['pulse_us'] is None,
         'idle_no_capture_play_follow_fault_null_required')
    return v
def load_module(path,expected,name):
    raw=read(path,expected);spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec);exec(compile(raw,path,'exec'),module.__dict__);return module
def old_live(p):
    checks(p);u=show();o=p['original']
    need(u['MainPID']==str(o['supervisor']['pid']) and u['ActiveState']=='active' and not u.get('Job'),
         'exact_original_service_required')
    need(same(process(o['supervisor']['pid']),o['supervisor']) and same(process(o['child']['pid']),o['child']),
         'original_owners_changed')
    need(u['DropInPaths']==o['properties']['DropInPaths']
         and exec_argv(u['ExecStart'])==exec_argv(o['properties']['ExecStart']),'original_unit_selection_changed')
    for k in ('Restart','SendSIGKILL','TimeoutStopUSec'):need(u[k]==o['properties'][k],'original_unit_properties_changed')
    need(u.get('UnitFileState')=='enabled','existing_persistent_enabled_unit_required')
    state(p);return u


def payload(p,archive):
    startup=checks(p);o=p['original'];files={}
    for rel,expected in o['pins'].items():
        relative(rel);files['runtime/aura/'+rel]=read(o['runtime']+'/aura/'+rel,expected,aliases=o['aliases'])
    raw=read(archive,p['overlay_sha256'],33554432)
    manifest=parse(read(p['overlay_manifest'],p['overlay_manifest_sha256']))
    need(manifest['based_on_startup_sha256']==o['startup_sha256'] and manifest['business_mode']=='UNCHANGED_LEGACY'
         and manifest['enable_board_business'] is False and manifest['synthetic_store_included'] is False,'legacy_only_overlay_required')
    for rel,expected in manifest['before_sha256'].items():need(o['pins'].get(rel)==expected,'overlay_before_pin_conflict')
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        rows=z.infolist();need(len(rows)==len(manifest['files']) and len({v.filename for v in rows})==len(rows),'exact_overlay_archive_required')
        total=0
        for row in rows:
            name=relative(row.filename);total+=row.file_size
            need(not row.is_dir() and not stat.S_ISLNK(row.external_attr>>16) and row.file_size<=16777216
                 and total<=33554432 and name in manifest['files'],'bounded_source_assets_only')
            data=z.read(row);need(sha(data)==manifest['files'][name],'overlay_file_changed')
            if name=='config.fragment.json':fragment=parse(data);continue
            need(name.startswith('aura/') and not any(x in PurePosixPath(name).parts for x in ('cache','managed-runs','venv','.venv')),'overlay_path_not_source')
            rel=name[5:]
            if rel in o['pins']:need(rel in manifest['before_sha256'],'undeclared_original_override')
            if name.endswith('.py'):compile(data,name,'exec')
            files['runtime/'+name]=data
    allowed={'native_yuki','native_avatar','stable_avatar_fps','portrait_offload','character_pair',
             'formal_settings_paths','formal_stage_root','formal_static_cues'}
    need(set(fragment)==allowed,'exact_formal_fragment_fields_required')
    expected_settings={k:o['runtime']+'/avatar_'+suffix+'_settings.json' for k,suffix in
                       (('user','user'),('transcription','transcription'),('conversation','conversation'),('service','service'))}
    need(fragment['formal_settings_paths']==expected_settings and fragment['formal_stage_root']==
         o['runtime']+'/deliverables/2026-10-06_xilan_live','existing_business_paths_required')
    for path in expected_settings.values():need(Path(path).is_file(),'original_settings_path_missing')  # No contents read/copied.
    config=parse(files['runtime/aura/config/board_avatar_gtk.json']);need(not config.get('board_business'),'legacy_config_required')
    config.update(fragment);files['runtime/aura/config/board_avatar_gtk.json']=encoded(config)
    for row in p['public_copies']:
        rel=relative(row['target']);need(rel not in files,'public_resource_override')
        need(Path(row['declared']).resolve(strict=True)==Path(row['source']),'public_resource_alias_changed')
        data=read(row['source'],row['sha256']);need(len(data)==row['bytes'],'public_resource_size_changed');files[rel]=data
    new=copy.deepcopy(startup);new['runtime']=p['target']+'/runtime'
    pins={rel[len('runtime/aura/'):]:sha(data) for rel,data in files.items() if rel.startswith('runtime/aura/')}
    new['component_sha256']=pins;new['gui_sha256']=pins['tools/board_avatar_pan.py']
    need(set(k for k in startup if new[k]!=startup[k])<= {'runtime','component_sha256','gui_sha256'},'startup_rebase_scope_changed')
    files['startup/config.json']=encoded(new);files['startup/launcher.py']=read(o['launcher'],LAUNCHER_SHA)
    return files,manifest
def stage(p,archive,execute=False):
    old_live(p);files,overlay=payload(p,archive)
    mapping={k:dict(bytes=len(v),sha256=sha(v)) for k,v in files.items()}
    plan=dict(target=p['target'],files=mapping,overlay_sha256=p['overlay_sha256'],startup_launcher_sha256=LAUNCHER_SHA,
              existing_business_paths_preserved=True,home_or_database_copied=False)
    if not execute:return dict(status='INSPECTED_SOURCE_ONLY',files=len(files),target=p['target'],plan_sha256=sha(encoded(plan)))
    need(not Path(p['target']).exists() and not Path(p['control']).exists(),'new_namespaces_required')
    Path(p['target']).mkdir(mode=0o700,parents=True);Path(p['control']).mkdir(mode=0o700,parents=True)
    save(p,dict(phase='STAGING',policy_sha256=p['_sha256']))
    for rel,data in files.items():
        out=Path(p['target'])/rel;out.parent.mkdir(mode=0o700,parents=True,exist_ok=True);create(out,data)
    create(p['target']+'/publish_manifest.json',encoded(plan))
    save(p,dict(phase='STAGED',policy_sha256=p['_sha256'],manifest_sha256=sha(encoded(plan))))
    return dict(status='FORMAL_SOURCE_STAGED_OLD_GUI_UNCHANGED',target=p['target'],files=len(files))
def staged(p):
    checks(p);j=journal(p);need(j['policy_sha256']==p['_sha256'],'journal_policy_changed')
    plan=parse(read(p['target']+'/publish_manifest.json',j['manifest_sha256']))
    for rel,row in plan['files'].items():read(p['target']+'/'+relative(rel),row['sha256'])
    return j
def guard_paths(p):
    names=[Path(x).name for x in p['original']['properties']['DropInPaths'].split()]
    count=max([len(re.match('z*',x).group()) for x in names]+[0])+1
    persistent='/etc/systemd/system/'+UNIT+'.d/'+'z'*count+'-aura-xuefei-formal-20261030.conf'
    guard='/run/systemd/system/'+UNIT+'.d/'+'z'*(count+1)+'-aura-xuefei-safe-handoff-20261030.conf'
    need(len(Path(guard).name)<255 and all(x<Path(persistent).name for x in names),'dropin_sort_order')
    return persistent,guard
def guard(p):
    staged(p);u=old_live(p);persistent,path=guard_paths(p);need(not Path(path).exists() and not Path(persistent).exists(),'own_dropins_must_be_new')
    raw=b'[Service]\nRestart=no\nSendSIGKILL=no\nTimeoutStopSec=infinity\nTimeoutStartSec=180s\n'
    j=journal(p);j.update(phase='GUARD_INTENT',original_properties=u,guard=path,guard_sha256=sha(raw),persistent=persistent)
    save(p,j);Path(path).parent.mkdir(mode=0o755,parents=True,exist_ok=True);create(path,raw)
    command(['/bin/systemctl','daemon-reload']);guarded(p);j['phase']='GUARDED';save(p,j)
    return dict(status='GUARDED_OLD_GUI_STILL_RUNNING',guard=path,persistent_planned=persistent)
def guarded(p):
    staged(p);j=journal(p);read(j['guard'],j['guard_sha256']);u=show()
    need(u['Restart']=='no' and u['SendSIGKILL']=='no' and u['TimeoutStopUSec']=='infinity' and not u.get('Job'),'no_force_guards_required')
    expected=p['original']['properties']['DropInPaths'].split()+[j['guard']]
    if j.get('persistent_sha256'):read(j['persistent'],j['persistent_sha256']);expected.append(j['persistent'])
    need(sorted(u['DropInPaths'].split())==sorted(expected),'unreviewed_dropins_changed')
    return j,u


def current_window(p):
    j,u=guarded(p);pid=int(u['MainPID']);need(pid>0,'live_ui_owner_required')
    supervisor=process(pid);need(supervisor,'live_supervisor_required')
    if same(supervisor,p['original']['supervisor']):owner=p['original']['child']
    else:
        need(supervisor['argv']==new_command(p),'new_supervisor_entry_changed')
        launch=parse(read(p['target']+'/runtime/launch.json'));owner=process(launch['pid'])
        need(owner and owner['ppid']==pid and owner['argv'][:3]==['/usr/bin/python3','-B',p['target']+'/runtime/aura/tools/board_avatar_pan.py'],
             'new_gtk_owner_changed')
    actual=process(owner['pid']);need(same(actual,owner),'gtk_owner_changed');state(p)
    x=load_module(p['x11_source'],p['x11_sha256'],'_formal_verified_x11').X11(':0')
    try:
        rows=x.windows(owner['pid']);need(len(rows)==1 and rows[0]['normal'] and rows[0]['delete_supported'],'unique_normal_delete_window_required')
        proof=dict(boot_id=p['boot_id'],supervisor=supervisor,owner=actual,
                   window={k:rows[0][k] for k in ('window_id','title_sha256')},guard_sha256=j['guard_sha256'])
        need(same(process(owner['pid']),actual),'owner_changed_during_window_inspect')
        return dict(status='WINDOW_INSPECTED_NO_CLOSE',window=proof['window'],review_token=sha(encoded(proof))),proof
    finally:x.close()
def close(p,token,window_id):
    view,proof=current_window(p);need(view['review_token']==token and view['window']['window_id']==window_id,'explicit_exact_window_review_required')
    again,second=current_window(p);need(proof==second,'window_or_owner_changed_before_close')
    x=load_module(p['x11_source'],p['x11_sha256'],'_formal_verified_x11_send').X11(':0')
    try:
        rows=x.windows(proof['owner']['pid']);need(len(rows)==1 and rows[0]['window_id']==window_id
             and rows[0]['title_sha256']==proof['window']['title_sha256'] and rows[0]['delete_supported'],'window_changed_before_send')
        need(same(process(proof['owner']['pid']),proof['owner']),'gtk_changed_before_send');x.send_delete(window_id)
    finally:x.close()
    deadline=time.monotonic()+40
    while time.monotonic()<deadline:
        a,b=process(proof['owner']['pid']),process(proof['supervisor']['pid']);u=show()
        if not same(a,proof['owner']) and not same(b,proof['supervisor']) and u['MainPID']=='0' and not u.get('Job'):
            j=journal(p);j.update(phase='NORMAL_CLOSED',closed_owner=proof['owner'],closed_supervisor=proof['supervisor']);save(p,j)
            return dict(status='GTK_AND_SUPERVISOR_NATURALLY_EXITED',forced_action=False)
        time.sleep(.2)
    return dict(status='NORMAL_CLOSE_PENDING_GUARD_RETAINED',forced_action=False)
def new_command(p):return ['/usr/bin/python3','-B',p['target']+'/startup/launcher.py','--config',p['target']+'/startup/config.json']
def inactive(p):
    j,u=guarded(p);need(u['MainPID']=='0' and u['ActiveState']=='inactive' and not u.get('Job'),'inactive_ownerless_unit_required')
    need(not same(process(p['original']['supervisor']['pid']),p['original']['supervisor'])
         and not same(process(p['original']['child']['pid']),p['original']['child']),'old_owners_still_alive')
    return j
def publish(p):
    j=inactive(p);need(not j.get('persistent_sha256'),'formal_dropin_already_installed')
    raw=('[Service]\nExecStart=\nExecStart='+' '.join(new_command(p))+'\nTimeoutStartSec=180s\n').encode()
    Path(j['persistent']).parent.mkdir(mode=0o755,parents=True,exist_ok=True);create(j['persistent'],raw)
    j.update(phase='PERSISTENT_INTENT',persistent_sha256=sha(raw));save(p,j);command(['/bin/systemctl','daemon-reload'])
    _,u=guarded(p);need(exec_argv(u['ExecStart'])==' '.join(new_command(p)),'new_execstart_not_effective')
    command(['/bin/systemctl','--no-block','start',UNIT]);j['phase']='NEW_STARTING';save(p,j)
    return dict(status='PERSISTENT_FORMAL_START_REQUESTED',target=p['target'],readiness_seconds=180)
def ready(p,original=False):
    deadline=time.monotonic()+180;last='waiting'
    while time.monotonic()<deadline:
        removed_guard=None
        try:
            j,u=guarded(p);need(u['ActiveState']=='active' and int(u['MainPID'])>0,'service_not_active')
            owner=process(int(u['MainPID']));need(owner and owner['argv']==(p['original']['supervisor']['argv'] if original else new_command(p)), 'supervisor_entry_changed')
            v=state(p)
            if not original:
                pair=v.get('character_pair',{});display=v.get('avatar_display',{})
                need(pair.get('state')=='READY' and pair.get('profile_version')==PAIR and pair.get('prompt_sha256')==PROMPT,
                     'formal_pair_not_ready')
                need(display.get('kind')=='native_yuki_egl' and display.get('frames',0)>=1,'native_first_swap_not_ready')
            need(not u.get('Job'),'service_job_pending')
            removed_guard=read(j['guard'],j['guard_sha256']);Path(j['guard']).unlink();command(['/bin/systemctl','daemon-reload'])
            final=show();need(final['MainPID']==str(owner['pid']) and not final.get('Job'),'owner_changed_during_guard_removal')
            for k in ('Restart','SendSIGKILL','TimeoutStopUSec'):need(final[k]==j['original_properties'][k],'original_stop_policy_not_restored')
            need(exec_argv(final['ExecStart'])==' '.join(p['original']['supervisor']['argv'] if original else new_command(p)),'persistent_exec_changed')
            j.update(phase='ROLLED_BACK' if original else 'COMMITTED',final_owner=owner,guard_removed=True);save(p,j)
            return dict(status='ORIGINAL_RESTORED' if original else 'FORMAL_CHARACTER_PERSISTENT_COMMITTED',main_pid=owner['pid'],
                        guard_removed=True,persistent_dropin=None if original else j['persistent'],speech_model_ready_claimed=False)
        except (OSError,ValueError,subprocess.TimeoutExpired) as exc:
            last=type(exc).__name__
            if removed_guard is not None:
                # A post-removal verification failure restores only our exact
                # no-force guard. Never leave a failed handoff unprotected.
                if not Path(j['guard']).exists():create(j['guard'],removed_guard)
                read(j['guard'],j['guard_sha256']);command(['/bin/systemctl','daemon-reload'])
                j.update(phase='POSTCHECK_FAILED_GUARDED',guard_removed=False);save(p,j)
                return dict(status='READINESS_POSTCHECK_FAILED_GUARD_RETAINED',error_type=last,forced_action=False)
        time.sleep(.5)
    return dict(status='READINESS_TIMEOUT_GUARD_RETAINED',error_type=last,readiness_seconds=180,forced_action=False)
def rollback_prepare(p):
    j=staged(p)
    if j.get('guard_removed'):
        raw=b'[Service]\nRestart=no\nSendSIGKILL=no\nTimeoutStopSec=infinity\nTimeoutStartSec=180s\n'
        need(sha(raw)==j['guard_sha256'] and not Path(j['guard']).exists(),'exact_guard_restore_required')
        create(j['guard'],raw);command(['/bin/systemctl','daemon-reload']);j['guard_removed']=False;save(p,j)
    guarded(p);return dict(status='ROLLBACK_GUARDED_USE_WINDOW_INSPECT_THEN_NORMAL_CLOSE')
def rollback_start(p):
    j=inactive(p)
    if j.get('persistent_sha256'):
        read(j['persistent'],j['persistent_sha256']);Path(j['persistent']).unlink();j.pop('persistent_sha256');save(p,j)
    command(['/bin/systemctl','daemon-reload']);_,u=guarded(p)
    need(exec_argv(u['ExecStart'])==exec_argv(p['original']['properties']['ExecStart']),'original_exec_not_restored')
    command(['/bin/systemctl','--no-block','start',UNIT]);j['phase']='ORIGINAL_STARTING';save(p,j)
    return dict(status='ORIGINAL_START_REQUESTED_NORMAL_READY_REQUIRED',readiness_seconds=180)


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('action',nargs='?',default='inspect',choices=('inspect','stage','startup-check','guard','window-inspect',
        'normal-close','publish','ready','rollback-prepare','rollback-start','rollback-ready'))
    ap.add_argument('--policy',required=True);ap.add_argument('--policy-sha256',required=True);ap.add_argument('--overlay')
    ap.add_argument('--review-token');ap.add_argument('--window-id',type=lambda x:int(x,0));a=ap.parse_args()
    try:
        need(os.name=='posix' and os.geteuid()==0,'root_posix_only');p=parse(read(a.policy,a.policy_sha256));p['_sha256']=a.policy_sha256
        if a.action in ('inspect','stage'):
            need(a.overlay,'overlay_archive_argument_required');result=stage(p,a.overlay,a.action=='stage')
        elif a.action=='startup-check':
            staged(p);result=dict(status='STARTUP_SOURCE_PREFLIGHT_ONLY',output=command(new_command(p)+['--preflight'],20))
        elif a.action=='guard':result=guard(p)
        elif a.action=='window-inspect':result=current_window(p)[0]
        elif a.action=='normal-close':result=close(p,a.review_token,a.window_id)
        elif a.action=='publish':result=publish(p)
        elif a.action in ('ready','rollback-ready'):result=ready(p,a.action=='rollback-ready')
        elif a.action=='rollback-prepare':result=rollback_prepare(p)
        else:result=rollback_start(p)
        print(json.dumps(result,ensure_ascii=True));return 3 if result['status'].endswith(('GUARD_RETAINED','PENDING')) else 0
    except Exception as exc:
        print(json.dumps(dict(status='REFUSED_GUARD_RETAINED_NO_FORCE',error_type=type(exc).__name__,
             error_code=str(exc) if isinstance(exc,ValueError) and re.fullmatch('[a-z0-9_]{1,120}',str(exc)) else 'preflight_or_operation_failed',forced_action=False)))
        return 2
if __name__=='__main__':raise SystemExit(main())
