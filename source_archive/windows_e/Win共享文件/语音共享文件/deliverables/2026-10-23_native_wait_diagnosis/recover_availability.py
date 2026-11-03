"""Once-only recovery of unchanged services after completed optional faults."""
import fcntl,hashlib,json,os,subprocess,sys,time
from pathlib import Path

BOOT='7924ac9f-311d-4fcd-98be-57bf023cf1aa'
UNIT=Path('/etc/systemd/system/aura-camera-ui.service')
UNIT_SHA='29786434df9bb9b94a8e640a7a48db47019c224d3876037ce27d3467bb2f5512'
GUI_ROOT=Path('/home/root/aura-video-cpu-20261023/66cde810eb059dce')
CTRL_SHA='1b782de0126abbbe6550050e41bfb2db22137449daf0c779285279e8cfee12b3'
OLD_CAMERA=499773
CAMERA='aura-camera-ui.service';GUI='aura-avatar-ui.service'
SOURCE=Path(sys._getframe().f_code.co_filename).resolve()
ROOT=Path('/home/root/aura-native-wait-20261023/recovery')/hashlib.sha256(SOURCE.read_bytes()).hexdigest()[:16]
ROOT.mkdir(parents=True,exist_ok=True,mode=0o700)
assert not sys.flags.optimize
sys.dont_write_bytecode=True
assert hashlib.sha256((GUI_ROOT/'gui_trial.py').read_bytes()).hexdigest()==CTRL_SHA
sys.path.insert(0,str(GUI_ROOT));import gui_trial as g

def verify_constants():
    assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==BOOT
    assert g.sha(UNIT)==UNIT_SHA and g.sha(GUI_ROOT/'gui_trial.py')==CTRL_SHA
def owners():
    found=[]
    for p in Path('/proc').iterdir():
        if not p.name.isdigit():continue
        try:
            for fd in (p/'fd').iterdir():
                try:value=os.readlink(fd)
                except (FileNotFoundError,ProcessLookupError):continue
                if value=='/dev/dri/renderD128' or value.startswith('/dev/dpu'):
                    found.append(int(p.name));break
        except (FileNotFoundError,PermissionError,ProcessLookupError):pass
    return sorted(found)
def save(value):g.atomic(ROOT/'report.json',value)
def wait_health(pid=None,seconds=40,exclude_pid=None):
    deadline=time.monotonic()+seconds;last=''
    while time.monotonic()<deadline:
        try:
            h=g.camera()
            if pid is not None:assert h['pid']==pid
            if exclude_pid is not None:assert h['pid']!=exclude_pid
            return h
        except Exception as error:last=type(error).__name__+': '+str(error);time.sleep(.4)
    raise RuntimeError('Camera health not available: '+last)
def stable_state(unit,seconds=40):
    deadline=time.monotonic()+seconds
    while time.monotonic()<deadline:
        value=g.prop(unit,'ActiveState')
        if value not in ('activating','deactivating','reloading'):return value
        time.sleep(.3)
    raise RuntimeError('Service transition did not settle: '+unit)
def cmdline(pid):return (Path('/proc')/str(pid)/'cmdline').read_bytes().split(b'\0')[:-1]
def arm_guard(report):
    if g.prop(report['guard']+'.timer','ActiveState')!='active':
        report['guard']='aura-availability-guard-'+ROOT.name+'-'+str(os.getpid());report['guard_armed']=False;save(report)
        g.command(['systemd-run','--unit='+report['guard'],'--on-active=180s','--property=RuntimeMaxSec=300',
                   '/usr/bin/python3','-B',str(SOURCE),'--guard'])
    assert g.prop(report['guard']+'.timer','ActiveState')=='active'
    report['guard_armed']=True;save(report)
def ensure_finished(report):
    """Idempotent steps, also used by an independent deadline guard."""
    verify_constants();meta=json.loads((GUI_ROOT/'session.json').read_text())
    state=stable_state(CAMERA);pid=int(g.prop(CAMERA,'MainPID'))
    if pid==OLD_CAMERA and state=='active':
        g.verify(GUI_ROOT,meta)
        latest=g.camera()
        assert latest['pid']==OLD_CAMERA and not latest['owner_fenced']
        assert latest['worker_alive'] and not latest['worker_faults']
        assert len(latest['fault_events'])==3 and all(e['native_completed']==1 and e['native_status']==0
            and not e['native_failed'] and not e['body_failed'] for e in latest['fault_events'])
        report['phase']='STOPPING_IDLE_GUI';save(report)
        if stable_state(GUI)=='active':
            g.idle();g.stop_gui(GUI_ROOT,meta)
        g.pcm_closed()
        report['phase']='STOPPING_SAME_CAMERA';save(report)
        g.command(['systemctl','stop',CAMERA],timeout=40)
        stop={key:g.prop(CAMERA,key) for key in ('Result','ExecMainStatus')}
        report['camera_stop_result']=stop;save(report)
        assert stop['Result']=='success' and stop['ExecMainStatus']=='0'
        assert not Path('/proc/499773').exists() and not owners()
        state=g.prop(CAMERA,'ActiveState')
    if state in ('inactive','failed'):
        g.pcm_closed();assert not owners()
        assert g.prop(CAMERA,'Result')=='success','Refuse new owner after unconfirmed camera exit'
        report['phase']='STARTING_SAME_CAMERA';save(report)
        g.command(['systemctl','start','--no-block',CAMERA])
    h=wait_health(exclude_pid=OLD_CAMERA);new_pid=h['pid']
    assert int(g.prop(CAMERA,'MainPID'))==new_pid
    # Rebase only the PID of an explicitly restarted, identical camera unit.
    # The GUI controller source, code/config pins, override and preferences
    # remain unchanged. Its default rollback check now describes this process.
    assert [part.decode() for part in cmdline(new_pid)]==report['original_camera_command']
    assert [str(p) for p in g.retained().runtime_for(new_pid)]==report['original_camera_runtime']
    g.retained().single_owner(new_pid)
    meta=json.loads((GUI_ROOT/'session.json').read_text())
    assert meta['camera_pid'] in (OLD_CAMERA,new_pid)
    rebased=dict(meta,camera_pid=new_pid);g.verify(GUI_ROOT,rebased)
    g.atomic(GUI_ROOT/'session.json',rebased);meta=rebased
    report['gui_restore_context_rebased']={'old_camera_pid':OLD_CAMERA,'new_camera_pid':new_pid,
        'unit_sha256':UNIT_SHA,'gui_controller_sha256':CTRL_SHA}
    report['phase']='RESTORING_SAME_GUI';save(report)
    if g.prop(GUI,'ActiveState') in ('inactive','failed'):
        g.start_gui(GUI_ROOT,meta)
    else:
        deadline=time.monotonic()+110
        while time.monotonic()<deadline:
            try:g.idle();break
            except Exception:time.sleep(.5)
        else:raise RuntimeError('GUI did not become idle/ready')
    g.set_page(report['original_page']);g.verify(GUI_ROOT,meta)
    return new_pid

def run(is_guard=False):
    with (ROOT/'recovery.lock').open('a+') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        if (ROOT/'report.json').exists():
            report=json.loads((ROOT/'report.json').read_text())
            if report.get('complete'):return report
        else:
            assert not is_guard
            verify_constants();meta=json.loads((GUI_ROOT/'session.json').read_text());g.verify(GUI_ROOT,meta)
            u=g.idle();h=g.camera();assert h['pid']==OLD_CAMERA and not h['owner_fenced']
            assert h['worker_alive'] and not h['worker_faults']
            assert h['optional']['yunet']['disabled'] and h['optional']['yunet']['overruns']==2
            assert h['optional']['sface']['disabled'] and h['optional']['sface']['overruns']==1
            assert len(h['fault_events'])==3
            assert all(e['native_completed']==1 and e['native_status']==0 and not e['native_failed']
                       and not e['body_failed'] for e in h['fault_events'])
            assert owners()==[OLD_CAMERA];g.retained().single_owner(OLD_CAMERA)
            accepted=Path('/home/root/aura-vision-reliability-20261023/f7624754038f3669/report.json')
            assert g.sha(accepted)=='070ca6e5377a0c692cf4036b993963afd03e5e7cf49514932c5135aeb563085d'
            source=json.loads(accepted.read_text())
            base=Path('/home/root/aura-dpu-vision-20261021/postpower-retry-live/release-reliability-f7624754038f-450136/aura')
            for name,row in source['source_manifest'].items():assert g.sha(base/name)==row['sha256']
            report={'complete':False,'passed':False,'recovery_only':True,'root_cause_fixed':False,
                'phase':'ARMING','before':h,'original_page':u['ui_page'],'old_gui_pid':int(g.prop(GUI,'MainPID')),
                'unit_sha256':UNIT_SHA,'guard':'aura-availability-guard-'+ROOT.name,
                'original_gui_command':[part.decode() for part in g.gui_command()],
                'original_camera_command':[part.decode() for part in cmdline(OLD_CAMERA)],
                'original_camera_runtime':[str(p) for p in g.retained().runtime_for(OLD_CAMERA)],
                'kernel_cursor':g.retained().kernel_cursor()}
            (ROOT/'gui-session-before.json').write_bytes((GUI_ROOT/'session.json').read_bytes());save(report)
        if is_guard:assert report.get('guard_armed'),'Guard did not originate from an armed transition'
        else:arm_guard(report)
        try:
            with (GUI_ROOT/'restore.lock').open('a+') as gui_lock:
                fcntl.flock(gui_lock,fcntl.LOCK_EX)
                new_pid=ensure_finished(report)
            report['new_camera_pid']=new_pid
            report['phase']='OBSERVING_AVAILABILITY';save(report)
            initial=wait_health(new_pid);time.sleep(10);final=wait_health(new_pid)
            report['after']=final;report['new_gui_pid']=int(g.prop(GUI,'MainPID'))
            assert [part.decode() for part in g.gui_command()]==report['original_gui_command']
            report['new_usb_audio_warnings']=g.retained().audio_warnings(report['kernel_cursor'])
            report['rollback_check']=g.restore(GUI_ROOT,'check')
            report['counter_scope']='Old process faults/gap preserved in before; new process counters restart by explicit service restart'
            report['old_faults_preserved']={'yunet':2,'sface':1,'gaps':report['before']['gaps']}
            report['passed']=(final['identity_ready'] and final['feature_inference']['ready'] and final['worker_alive']
                and final['face_backend']=='DPU_YUNET_INT8' and not final['owner_fenced']
                and all(not row['disabled'] for row in final['optional'].values()) and report['new_usb_audio_warnings']==0)
            report['observed_yolo_frames']=final['detected_frames']-initial['detected_frames']
            report['phase']='AVAILABILITY_RESTORED' if report['passed'] else 'RUNNING_WITH_RECORDED_DEGRADATION'
            report['transition_finished']=True
            report.pop('error',None)
        except Exception as error:
            report.setdefault('attempt_errors',[]).append({'guard':is_guard,'error':type(error).__name__+': '+str(error)})
            report['error']=type(error).__name__+': '+str(error);report['phase']='RECOVERY_ERROR'
            if is_guard:
                report['guard_attempt_finished']=True;report['guard_retries_automatically']=False
            # Leave the independent guard armed for an interrupted owned
            # transition. It never installs another camera version or owner.
        if report.get('transition_finished'):
            g.command(['systemctl','stop',report['guard']+'.timer'])
            report['guard_state']=g.prop(report['guard']+'.timer','ActiveState')
            report['complete']=True
        save(report);return report

args=sys.argv[1:];assert args in ([],['--run'],['--guard'])
if args in (['--run'],['--guard']):print(json.dumps(run(args==['--guard'])))
else:
    assert not (ROOT/'report.json').exists()
    unit='aura-availability-recovery-'+ROOT.name
    g.command(['systemd-run','--unit='+unit,'--property=RuntimeMaxSec=240','/usr/bin/python3','-B',str(SOURCE),'--run'])
    print(json.dumps({'started':True,'unit':unit,'report':str(ROOT/'report.json')}))
