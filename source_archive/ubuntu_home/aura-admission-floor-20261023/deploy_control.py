"""Owned promotion with preserved optional protection and protected old-code rollback."""
import copy,fcntl,hashlib,importlib.util,json,os,shutil,subprocess,sys,time,traceback
from pathlib import Path

BOOT='008f3e1b-c627-4b98-b120-d2a460cdbcbe'
PARENT=Path('/home/root/aura-dpu-vision-20261021/postpower-retry-live/release-sface-recovery-4bcbe0999c62a348')
PARENT_OVERRIDE=Path('/run/systemd/system/aura-camera-ui.service.d/zz-aura-sface-recovery-4bcbe0999c62a348.conf')
PARENT_OVERRIDE_SHA='08ff0218e7cd92ea191fe9ee833d6ff3991f417f01a37213e7fbedf8c59f2d78'
UNIT=Path('/etc/systemd/system/aura-camera-ui.service')
PARENT_UNIT_SHA='29786434df9bb9b94a8e640a7a48db47019c224d3876037ce27d3467bb2f5512'
GUI_CONTEXT=Path('/home/root/aura-sface-recovery-20261023/promotion/4bcbe0999c62a348/gui-context-5842')
GUI_CONTROL_SHA='1ae8e61ac26be070315ba6bf855a01dd792c300396bd80f94d3b72929c08c32f'
OLD_PID=5842
sys.dont_write_bytecode=True
assert hashlib.sha256((GUI_CONTEXT/'gui_trial.py').read_bytes()).hexdigest()==GUI_CONTROL_SHA
sys.path.insert(0,str(GUI_CONTEXT));import gui_trial as g
# Revalidate the unchanged GUI source/config against this externally changed
# boot in our private context; never rewrite the historical rollback context.
g.BOOT=BOOT

def digest(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def atomic_bytes(path,raw):
    temp=path.with_name(path.name+'.tmp-'+str(os.getpid()))
    with temp.open('xb') as stream:stream.write(raw);stream.flush();os.fsync(stream.fileno())
    os.replace(temp,path)
def save(root,report):g.atomic(root/'report.json',report)
def override_path(root):
    return Path('/run/systemd/system/aura-camera-ui.service.d')/('zzz-aura-admission-floor-'+root.name+'.conf')
def effective_marker(root):
    assert digest(UNIT)==PARENT_UNIT_SHA
    p=override_path(root)
    return digest(p) if p.exists() else PARENT_UNIT_SHA
def dropin(unit):
    lines=unit.decode().splitlines()
    selected=[line for line in lines if line.startswith(('ExecStart=','WorkingDirectory=')) and line!='ExecStart=']
    assert len(selected)==2
    return ('[Service]\nExecStart=\n'+'\n'.join(selected)+'\n').encode()
def get_health():return g.get(8790,'/health')
def snapshot_seed():
    until=time.monotonic()+5
    while time.monotonic()<until:
        value=get_health();s=value['dpu_schedule']
        if s['active'] is None and not s['waiting_primary']:return value
        time.sleep(.015)
    raise RuntimeError('No idle owner snapshot available')
def wait_camera(expected_root,timeout=45):
    until=time.monotonic()+timeout;last=''
    while time.monotonic()<until:
        try:
            h=get_health();pid=h['pid']
            assert pid!=OLD_PID
            args=(Path('/proc')/str(pid)/'cmdline').read_bytes().split(b'\0')
            assert str(expected_root).encode() in b' '.join(args)
            assert int(g.prop(g.CAMERA,'MainPID'))==pid
            g.retained().single_owner(pid)
            return h
        except Exception as error:last=type(error).__name__+': '+str(error);time.sleep(.4)
    raise RuntimeError('New camera failed health: '+last)

def prepare(root,source,pins):
    assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==BOOT
    assert digest(UNIT)==PARENT_UNIT_SHA and int(g.prop(g.CAMERA,'MainPID'))==OLD_PID
    assert digest(PARENT_OVERRIDE)==PARENT_OVERRIDE_SHA
    assert not override_path(root).exists()
    for name,pin in json.loads((root/'baseline-manifest.json').read_text()).items():
        assert digest(PARENT/'aura'/name)==pin,'Parent runtime changed'
    old_meta=json.loads((GUI_CONTEXT/'session.json').read_text());old_meta['camera_pid']=OLD_PID
    if digest(g.PREF) not in old_meta['allowed_preference_hashes']:
        assert json.loads(g.PREF.read_text())==json.loads((GUI_CONTEXT/'preference.original').read_text())
        old_meta['allowed_preference_hashes'].append(digest(g.PREF))
    g.verify(GUI_CONTEXT,old_meta)
    g.idle();before=snapshot_seed();s=before['dpu_schedule']
    assert not s['owner_fenced'] and s['yunet_recovery']['phase']=='RUNNING'
    assert all(not s['optional'][kind]['disabled'] and s['optional'][kind]['overruns']==0 for kind in ('yunet','sface'))
    assert before['identity']['face_targets']['worker_alive']
    assert len(s['optional_diagnostics']['fault_events'])==0
    release=PARENT.parent/('release-admission-floor-'+root.name)
    release.mkdir();shutil.copytree(PARENT/'aura',release/'aura',ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
    baseline={}
    for name,meta in pins.items():
        path=release/'aura'/name
        if path.exists():baseline[name]=digest(path)
        path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes((root/'candidate/aura'/name).read_bytes())
        assert digest(path)==meta
    for name in ('runtime_entry.py','gil_camera_launcher.py'):
        shutil.copyfile(PARENT/name,release/name)
    original_unit=PARENT_OVERRIDE.read_bytes();(root/'unit.original').write_bytes(original_unit)
    seed={'schema':'aura-dpu-protection-handoff-1','boot':BOOT,'source_pid':OLD_PID,
        'source_birth_ticks':int((Path('/proc')/str(OLD_PID)/'stat').read_text().rsplit(')',1)[1].split()[19]),
        'source_unit_sha256':PARENT_UNIT_SHA,'source_manifest_sha256':hashlib.sha256(json.dumps(baseline,sort_keys=True).encode()).hexdigest(),
        'captured_mono_ns':time.monotonic_ns(),'schedule':s,'feature_inference':before['identity']['feature_inference']}
    seed_path=root/'protection-seed.json';g.atomic(seed_path,seed)
    seed_pin={'path':str(seed_path),'sha256':digest(seed_path)}
    # Exercise the exact old fault snapshot against the new parser before any
    # service mutation. This private copy never consumes the live startup seed.
    validation=root/'validation-seed.json';validation.write_bytes(seed_path.read_bytes())
    program='''import json,sys
from pathlib import Path
sys.path.insert(0,sys.argv[1])
from board.vision.dpu_vision_schedule import DpuVisionSchedule
from board.vision.dpu_protection_handoff import restore_protection
s=DpuVisionSchedule(yunet_recovery=True,sface_recovery=True)
restore_protection(s,{'path':sys.argv[2],'sha256':sys.argv[3]},boot_id=sys.argv[4])
assert s.yunet_recovery.phase=='RUNNING' and s.sface_recovery.phase=='RUNNING'
print(json.dumps({'passed':True,'sface_phase':s.sface_recovery.phase,'yunet_phase':s.yunet_recovery.phase}))
'''
    checked=subprocess.run(['/usr/bin/python3','-B','-c',program,str(release/'aura'),str(validation),digest(validation),BOOT],
        stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,timeout=10)
    assert checked.returncode==0,'Protection migration preflight failed: '+checked.stderr[-1500:]
    config=json.loads((PARENT/'board_camera_ui.json').read_text())
    config.update(sface_dpu_recovery=True,dpu_protection_seed=seed_pin,optional_admission_floor_ms=30)
    (release/'board_camera_ui.json').write_text(json.dumps(config,indent=2)+'\n')
    unit=dropin(original_unit.decode().replace(str(PARENT),str(release)).encode())
    assert unit!=original_unit and str(PARENT).encode() not in unit
    (root/'unit.candidate').write_bytes(unit)
    rollback=root/'protected_rollback_entry.py'
    handoff=release/'aura/board/vision/dpu_protection_handoff.py'
    rollback_pins={str(p):digest(p) for p in (handoff,PARENT/'runtime_entry.py',PARENT/'gil_camera_launcher.py',
        PARENT/'aura/board/vision/dpu_vision_schedule.py',PARENT/'aura/board/vision/ui_camera_service.py',
        PARENT/'aura/board/vision/dpu_sface.py')}
    rollback_config=json.loads((PARENT/'board_camera_ui.json').read_text());rollback_config.pop('dpu_protection_seed',None)
    g.atomic(root/'rollback-camera-config.json',rollback_config)
    rollback_pins[str(root/'rollback-camera-config.json')]=digest(root/'rollback-camera-config.json')
    rollback_meta=dict(boot=BOOT,parent=str(PARENT),pins=rollback_pins,handoff_module=str(handoff),seed=seed_pin)
    g.atomic(root/'rollback-metadata.json',rollback_meta)
    rollback_unit=dropin(original_unit.decode().replace(str(PARENT/'runtime_entry.py'),str(rollback))
        .replace(str(PARENT/'board_camera_ui.json'),str(root/'rollback-camera-config.json')).encode())
    (root/'unit.rollback').write_bytes(rollback_unit)
    initial=g.ui()
    report={'complete':False,'accepted':False,'passed':False,'phase':'PREPARED','boot':BOOT,'before':g.camera(),
        'old_camera_pid':OLD_PID,'old_gui_pid':int(g.prop(g.GUI,'MainPID')),'original_page':initial['ui_page'],
        'release':str(release),'candidate_unit_sha256':digest(root/'unit.candidate'),'rollback_unit_sha256':digest(root/'unit.rollback'),
        'candidate_pins':pins,'baseline_pins':baseline,'seed':seed_pin,'source_sha256':digest(source),
        'runtime_camera_override':str(override_path(root)),
        'deployment_scope':'Current boot runtime drop-in only; original /etc unit remains unchanged; next boot returns original entry without this seed',
        'guard':'aura-sface-recovery-guard-'+root.name,'kernel_cursor':g.retained().kernel_cursor(),
        'gui_runtime_unchanged':True,'root_cause_fixed':False,'old_faults_preserved_in_seed':True}
    report['seed_validation']=json.loads(checked.stdout)
    g.atomic(root/'gui-session.original.json',old_meta)
    g.atomic(root/'gui-preference-original.sha.json',{'sha256':digest(g.PREF)})
    save(root,report);return report

def gui_context_for(root,report,pid,unit_sha):
    """Create a new pinned GUI-only rollback context; do not rewrite the old one."""
    assert unit_sha==PARENT_UNIT_SHA
    folder=root/('gui-context-'+str(pid));folder.mkdir(exist_ok=True)
    raw=(GUI_CONTEXT/'gui_trial.py').read_text()
    assert raw.count(PARENT_UNIT_SHA)==1
    (folder/'gui_trial.py').write_text(raw.replace(PARENT_UNIT_SHA,unit_sha).replace('7924ac9f-311d-4fcd-98be-57bf023cf1aa',BOOT))
    controller_sha=digest(folder/'gui_trial.py')
    wrapper='''import hashlib,json,sys
from pathlib import Path
root=Path(__file__).resolve().parent
assert hashlib.sha256((root/'gui_trial.py').read_bytes()).hexdigest()==PIN
sys.path.insert(0,str(root));from gui_trial import restore
args=sys.argv[1:];assert args in ([],['--check'],['--restore'],['--guard'])
print(json.dumps(restore(root,'manual' if args==['--restore'] else 'guard' if args==['--guard'] else 'check')))
'''.replace('PIN',repr(controller_sha))
    (folder/'restore_previous.py').write_text(wrapper)
    meta=json.loads((root/'gui-session.original.json').read_text());meta['camera_pid']=pid
    for name in ('preference.original','override.candidate'):
        shutil.copyfile(GUI_CONTEXT/name,folder/name)
    # Existing protected files remain pinned; this context has its own controller.
    meta['protected'][str(folder/'gui_trial.py')]=digest(folder/'gui_trial.py')
    meta['protected'][str(folder/'restore_previous.py')]=digest(folder/'restore_previous.py')
    g.atomic(folder/'session.json',meta)
    spec=importlib.util.spec_from_file_location('_gui_context_'+unit_sha[:12],folder/'gui_trial.py')
    helper=importlib.util.module_from_spec(spec);spec.loader.exec_module(helper)
    helper.verify(folder,meta)
    return folder,helper,meta

def refresh_seed(root,report):
    latest=snapshot_seed();s=latest['dpu_schedule']
    assert latest['pid']==OLD_PID and not s['owner_fenced']
    assert s['yunet_recovery']['phase']=='RUNNING'
    assert all(not s['optional'][k]['disabled'] and s['optional'][k]['overruns']==0 for k in ('yunet','sface'))
    seed_path=Path(report['seed']['path']);seed=json.loads(seed_path.read_text())
    seed.update(captured_mono_ns=time.monotonic_ns(),schedule=s,feature_inference=latest['identity']['feature_inference'])
    assert not seed_path.with_name(seed_path.name+'.consumed').exists()
    g.atomic(seed_path,seed);pin={'path':str(seed_path),'sha256':digest(seed_path)}
    config_path=Path(report['release'])/'board_camera_ui.json'
    config=json.loads(config_path.read_text());config['dpu_protection_seed']=pin;g.atomic(config_path,config)
    meta=json.loads((root/'rollback-metadata.json').read_text());meta['seed']=pin;g.atomic(root/'rollback-metadata.json',meta)
    report.update(seed=pin,cutover_before=g.camera(),seed_snapshot_scope='After owned GUI stop, immediately before camera stop; not an atomic process-exit counter snapshot')
    save(root,report)

def stop_services(root,report,context=GUI_CONTEXT):
    meta=json.loads((context/'session.json').read_text())
    assert g.prop(g.CAMERA,'ActiveState')=='active'
    if effective_marker(root)==PARENT_UNIT_SHA:
        folder,helper,meta=gui_context_for(root,report,OLD_PID,PARENT_UNIT_SHA)
        if g.prop(g.GUI,'ActiveState')=='active':helper.stop_gui(folder,meta)
        # stop_gui can authorize an equivalent preference serialization. Keep
        # only the exact metadata it validated; never widen preference hashes.
        (root/'gui-session.original.json').write_bytes((folder/'session.json').read_bytes())
        refresh_seed(root,report)
    else:
        folder,helper,meta=gui_context_for(root,report,int(g.prop(g.CAMERA,'MainPID')),PARENT_UNIT_SHA)
        if g.prop(g.GUI,'ActiveState')=='active':helper.stop_gui(folder,meta)
    g.pcm_closed()
    g.command(['systemctl','stop',g.CAMERA],timeout=40)
    assert g.prop(g.CAMERA,'Result')=='success' and g.prop(g.CAMERA,'ExecMainStatus')=='0'
    assert not Path('/proc/'+str(meta['camera_pid'])).exists()

def rollback(root,report):
    if report.get('rolled_back'):return report
    current=effective_marker(root)
    assert current in (PARENT_UNIT_SHA,report['candidate_unit_sha256'],report['rollback_unit_sha256'])
    if g.prop(g.CAMERA,'ActiveState')=='active':
        assert not get_health()['dpu_schedule']['owner_fenced'],'Refuse replacement owner after unknown completion'
    if g.prop(g.CAMERA,'ActiveState')=='active':stop_services(root,report)
    else:
        assert g.prop(g.GUI,'ActiveState') in ('inactive','failed')
        g.pcm_closed()
    # Unknown native termination is never followed by a fresh owner.
    assert g.prop(g.CAMERA,'Result')=='success'
    path=override_path(root);path.parent.mkdir(parents=True,exist_ok=True)
    atomic_bytes(path,(root/'unit.rollback').read_bytes());g.command(['systemctl','daemon-reload'])
    g.command(['systemctl','start','--no-block',g.CAMERA])
    h=wait_camera(root);pid=h['pid'];s=h['dpu_schedule']
    assert s['rollback_holds_both_optional_tasks'] and all(s['optional'][k]['disabled'] for k in ('yunet','sface'))
    folder,helper,meta=gui_context_for(root,report,pid,PARENT_UNIT_SHA)
    helper.start_gui(folder,meta);helper.set_page(report['original_page'])
    report.update(rolled_back=True,phase='PROTECTED_OLD_CODE_RESTORED',rollback_camera_pid=pid,
        rollback_gui_pid=int(g.prop(g.GUI,'MainPID')),rollback_gui_context=str(folder),rollback_check=helper.restore(folder,'check'))
    save(root,report);return report

def run(root,source,pins,guard=False,manual=False):
    with (root/'deployment.lock').open('a+') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        if guard:
            report=json.loads((root/'report.json').read_text())
            if (report.get('accepted') and not manual) or report.get('rolled_back'):return report
            if manual:
                g.idle()
                report['guard']='aura-sface-recovery-manual-'+root.name+'-'+str(os.getpid())
                g.command(['systemd-run','--unit='+report['guard'],'--on-active=180s','--property=RuntimeMaxSec=180',
                    '/usr/bin/python3','-B',str(source),'--guard'])
                assert g.prop(report['guard']+'.timer','ActiveState')=='active'
                report['previously_accepted']=report.get('accepted',False)
                report['accepted']=False;report['manual_restore_requested']=True;save(root,report)
            try:rollback(root,report)
            except Exception as error:report['guard_restore_error']=type(error).__name__+': '+str(error)
            if report.get('rolled_back'):
                g.command(['systemctl','stop',report['guard']+'.timer'])
                report['guard_state']=g.prop(report['guard']+'.timer','ActiveState')
            save(root,report);return report
        report=prepare(root,source,pins);armed=False
        try:
            g.command(['systemd-run','--unit='+report['guard'],'--on-active=180s','--property=RuntimeMaxSec=180',
                '/usr/bin/python3','-B',str(source),'--guard'])
            assert g.prop(report['guard']+'.timer','ActiveState')=='active';armed=True
            report['phase']='STOPPING_PARENT';save(root,report)
            stop_services(root,report)
            # No native task can change the two disabled job states at this point.
            path=override_path(root);path.parent.mkdir(parents=True,exist_ok=True)
            atomic_bytes(path,(root/'unit.candidate').read_bytes());g.command(['systemctl','daemon-reload'])
            report['phase']='STARTING_CANDIDATE';save(root,report)
            g.command(['systemctl','start','--no-block',g.CAMERA])
            initial=wait_camera(Path(report['release']));pid=initial['pid']
            s=initial['dpu_schedule'];assert s['protection_handoff']['source_pid']==OLD_PID
            assert s['yunet_recovery']['phase']=='RUNNING'
            assert s['optional']['yunet']['overruns']==s['optional']['sface']['overruns']==0
            folder,helper,meta=gui_context_for(root,report,pid,PARENT_UNIT_SHA)
            helper.start_gui(folder,meta);helper.set_page(report['original_page'])
            report.update(phase='OBSERVING',candidate_camera_pid=pid,candidate_gui_pid=int(g.prop(g.GUI,'MainPID')),
                gui_context=str(folder),initial=helper.camera());save(root,report)
            started=time.monotonic();samples=[]
            for _ in range(12):
                time.sleep(5);h=helper.camera();assert h['pid']==pid
                samples.append(h)
                if h['owner_fenced'] or h['worker_faults']:raise RuntimeError('Candidate worker/native owner failed')
                if any(h['optional'][k]['overruns']>0 for k in ('yunet','sface')):
                    raise RuntimeError('New optional fault during recovery acceptance')
            final=samples[-1];full=get_health();policy=full['dpu_schedule']['sface_recovery']
            report.update(after=final,samples=samples,duration_seconds=time.monotonic()-started,sface_recovery=policy,
                new_sface_completed=final['feature_inference']['completed']-report['cutover_before']['feature_inference']['completed'],
                usb_audio_warning_delta=g.retained().audio_warnings(report['kernel_cursor']),rollback_check=helper.restore(folder,'check'))
            report['observed_yolo_hz']=(final['detected_frames']-report['initial']['detected_frames'])/report['duration_seconds']
            report['observed_face_processed_hz']=(final['face_processed']-report['initial']['face_processed'])/report['duration_seconds']
            report['primary_overrun_delta_window']=final['primary_overruns']-report['initial']['primary_overruns']
            report['startup_primary_overrun_delta']=report['initial']['primary_overruns']-report['cutover_before']['primary_overruns']
            healthy=(final['identity_ready'] and final['feature_inference']['ready'] and policy['phase']=='RUNNING'
                and policy['recoveries']==0 and not final['optional']['yunet']['disabled'] and final['recovery']['phase']=='RUNNING'
                and report['usb_audio_warning_delta']==0 and final['gaps']==0
                and report['observed_yolo_hz']>=9.5 and report['observed_face_processed_hz']>=3.5
                and report['primary_overrun_delta_window']==0)
            report['actual_recovery_validated']=False
            report['passed']=healthy
            if not report['passed']:raise RuntimeError('Recovery or waiting-for-real-input conditions not met')
            report.update(accepted=True,phase='ACTIVE_RECOVERY_ENABLED_NO_LIVE_FAULT_INJECTION',
                live_sface_sampled=report['new_sface_completed']>0)
        except Exception as error:
            report.update(error=type(error).__name__+': '+str(error),traceback=traceback.format_exc())
            try:rollback(root,report)
            except Exception as restore_error:report['restore_error']=type(restore_error).__name__+': '+str(restore_error)
        finally:
            if armed and (report.get('accepted') or report.get('rolled_back')):
                g.command(['systemctl','stop',report['guard']+'.timer'])
                report['guard_state']=g.prop(report['guard']+'.timer','ActiveState')
            report['complete']=True;save(root,report)
        return report
