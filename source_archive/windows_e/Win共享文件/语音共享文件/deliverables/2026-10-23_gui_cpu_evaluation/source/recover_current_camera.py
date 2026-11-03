"""One recorded restart of the same camera release after completed-only faults."""
import hashlib, json, os, subprocess, sys, time, urllib.request
from pathlib import Path

BOOT='7924ac9f-311d-4fcd-98be-57bf023cf1aa'
UNIT=Path('/etc/systemd/system/aura-camera-ui.service')
UNIT_SHA='29786434df9bb9b94a8e640a7a48db47019c224d3876037ce27d3467bb2f5512'
RELEASE=Path('/home/root/aura-dpu-vision-20261021/postpower-retry-live/release-reliability-f7624754038f-450136')
CONFIG=Path('/home/root/aura-dpu-vision-20261021/postpower-retry-live/release-sface-int8-9025bd49fe52-333217/board_identity.sface_int8.json')
DATABASE=Path('/home/root/.local/share/aura/sface-int8-12b2ff5c7de15713-333217.sqlite3')
PREF=Path('/home/root/.local/share/aura/handsfree_dialogue.json')
PINS={str(CONFIG):'398ece6a4d5d81076c9a4f9f40a43e97cedd469e0b47e3a835e589a2255ca6e3',
      str(DATABASE):'ee22b97dbaa6f29f5b76c18565acc4f597cd61c6090f1946b993d2a29ab8101a',
      str(RELEASE/'gui-runtime/aura/tools/libaura_pixels.so'):'201adac318e23411e608556fce360a335c422b129f64fa56e4d908ba39ab958f'}
CAMERA='aura-camera-ui.service';GUI='aura-avatar-ui.service'
SOURCE=Path(sys._getframe().f_code.co_filename).resolve()
ROOT=Path('/home/root/aura-gui-cpu-20261023/recovery')/hashlib.sha256(SOURCE.read_bytes()).hexdigest()[:16]
ROOT.mkdir(parents=True,exist_ok=True,mode=0o700)
op=urllib.request.build_opener(urllib.request.ProxyHandler({}))
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def command(args,timeout=15):return subprocess.check_output(args,timeout=timeout,stderr=subprocess.STDOUT,text=True).strip()
def prop(unit,field):return command(['systemctl','show',unit,'-p',field,'--value'])
def get(port,path):
    with op.open('http://127.0.0.1:'+str(port)+path,timeout=4) as r:return json.load(r)
def verify():
    assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==BOOT
    assert sha(UNIT)==UNIT_SHA
    for name,digest in PINS.items():assert sha(name)==digest,name
def owners():
    found=[]
    for p in Path('/proc').iterdir():
        if not p.name.isdigit():continue
        try:
            for fd in (p/'fd').iterdir():
                try:target=os.readlink(fd)
                except (FileNotFoundError,ProcessLookupError):continue
                if target.startswith('/dev/dpu') or target=='/dev/dri/renderD128':
                    found.append(int(p.name));break
        except (FileNotFoundError,PermissionError,ProcessLookupError):pass
    return sorted(found)
def owner_locks():
    lock=Path('/run/aura-person-dpu.lock').stat();found=[]
    for line in Path('/proc/locks').read_text().splitlines():
        parts=line.split()
        if len(parts)<6 or parts[1]!='FLOCK' or parts[3]!='WRITE':continue
        device=parts[5].split(':')
        if (len(device)==3 and int(device[0],16)==os.major(lock.st_dev)
                and int(device[1],16)==os.minor(lock.st_dev) and int(device[2])==lock.st_ino):
            found.append(int(parts[4]))
    return sorted(found)
def idle():
    s=get(8783,'/api/state')
    assert s.get('phase')=='IDLE' and s.get('audio_output_state')=='IDLE_READY'
    assert not s.get('playing') and not s.get('paused') and s.get('pending_job') is None
    assert s.get('local_recording',{}).get('state')=='IDLE'
    assert not s.get('local_transcription',{}).get('service',{}).get('pending')
    assert not s.get('handsfree_dialogue',{}).get('microphone_open')
    pan=s.get('manual_pan',{});assert not pan.get('automatic_following') and pan.get('pulse_us') is None
    return {k:s.get(k) for k in ('phase','audio_output_state','playing','paused')}
def health():
    h=get(8790,'/health');i=h['identity'];f=i['face_targets']
    return {'pid':h['pid'],'capture_frames':h['capture_frames'],'detected_frames':h['detected_frames'],
        'detection_hz':h['detection_hz'],'camera_error':h['camera_error'],'detector_error':h['detector_error'],
        'schedule':h['dpu_schedule'],'identity_ready':i['ready'],'identity_backend':i['backend'],
        'feature_inference':i['feature_inference'],'face_backend':f['backend'],'face_ready':f['ready'],
        'worker_alive':f['worker_alive'],'worker_faults':f['worker_faults'],
        'face_processed':f['processed'],'freshness_counters':f['freshness_metrics']['counters'],
        'fallback':f['inference']}
def atomic(path,value):
    temporary=path.with_suffix('.tmp')
    with temporary.open('w') as f:json.dump(value,f,indent=2);f.flush();os.fsync(f.fileno())
    os.replace(temporary,path)
def start_if_stopped():
    verify()
    state=prop(CAMERA,'ActiveState')
    if state in ('inactive','failed'):
        assert prop(CAMERA,'Result')=='success','Camera did not stop cleanly'
        assert not owners() and not owner_locks(),'A DPU owner remains; refusing another owner'
        command(['systemctl','start','--no-block',CAMERA])
    return {'state_before':state,'camera_pid':prop(CAMERA,'MainPID')}

def run():
    report={'complete':False,'passed':False,'phase':'PREFLIGHT','source_sha256':sha(SOURCE),
            'same_release_restart':True,'old_process_counters_preserved':True,'samples':[]}
    save=lambda:atomic(ROOT/'report.json',report)
    assert not (ROOT/'report.json').exists(),'Never overwrite recovery evidence'
    save();guard='aura-current-camera-restore-'+ROOT.name;armed=False;stopped=False
    try:
        verify();ui=idle();before=health();schedule=before['schedule'];jobs=schedule['optional']
        accepted=Path('/home/root/aura-vision-reliability-20261023/f7624754038f3669/report.json')
        assert sha(accepted)=='070ca6e5377a0c692cf4036b993963afd03e5e7cf49514932c5135aeb563085d'
        accepted_data=json.loads(accepted.read_text())
        for relative,record in accepted_data['source_manifest'].items():
            assert sha(RELEASE/'aura'/relative)==record['sha256'],relative
        assert before['pid']==450495 and prop(GUI,'MainPID')=='450525'
        assert before['identity_ready'] and before['worker_alive'] and not before['worker_faults']
        assert not schedule['owner_fenced'] and schedule['diagnostic_failures']==0
        assert jobs['yunet']['disabled'] and schedule['yunet_recovery']['phase']=='LATCHED'
        assert schedule['yunet_recovery']['reason']=='recovery_budget_exhausted'
        events=schedule['optional_diagnostics']['fault_events']
        assert jobs['yunet']['overruns']==3 and len(events)==3
        assert all(e['task_code']==1 and e['native_completed']==1 and e['native_status']==0
                   and not e['native_failed'] and not e['body_failed'] and not e['guard_exceeded'] for e in events)
        assert not jobs.get('sface',{}).get('disabled')
        for unit in ('aura-gui-profile-53e94ea536a981bf.service','aura-gui-profile-24983f6b6508cadb.service',
                     'aura-gui-exact-574e5989f5a99517.service','aura-gui-exact-5a47edaf1f81bd7e.service'):
            assert prop(unit,'ActiveState') in ('inactive','failed'),unit
        owned=owners();assert owned==owner_locks()==[450495],owned
        preference_sha=sha(PREF);gui_pid=prop(GUI,'MainPID');x_pid=prop('xserver-nodm.service','MainPID')
        report.update(before=before,ui_before=ui,unit_sha256=UNIT_SHA,preference_sha256=preference_sha,
                      gui_pid=gui_pid,xserver_pid=x_pid,owners_before=owned,phase='ARMING')
        save()
        command(['systemd-run','--unit='+guard,'--on-active=120s','--property=RuntimeMaxSec=30',
                 '/usr/bin/python3','-B',str(SOURCE),'--guard'])
        armed=True;assert prop(guard+'.timer','ActiveState')=='active'
        verify();idle();assert sha(PREF)==preference_sha
        assert health()['schedule']['owner_fenced'] is False
        report['phase']='STOPPING_SAME_CAMERA';save()
        command(['systemctl','stop',CAMERA],timeout=40);stopped=True
        report['stop_result']={field:prop(CAMERA,field) for field in ('Result','ExecMainCode','ExecMainStatus')}
        assert report['stop_result']['Result']=='success' and report['stop_result']['ExecMainStatus']=='0'
        assert not Path('/proc/450495').exists() and not owners() and not owner_locks()
        report['owners_after_stop']=owners();report['phase']='STARTING_SAME_CAMERA';save()
        start_if_stopped()
        deadline=time.monotonic()+40;last_error=''
        while time.monotonic()<deadline:
            try:
                after=health();s=after['schedule']
                assert after['pid']!=450495 and after['worker_alive'] and after['identity_ready']
                assert after['face_backend']=='DPU_YUNET_INT8' and not s['owner_fenced']
                assert not s['optional']['yunet']['disabled'] and after['detection_hz']>=9.
                assert after['feature_inference']['ready'] and after['identity_backend']=='DPU_SFACE_INT8'
                break
            except Exception as exc:last_error=type(exc).__name__+': '+str(exc);time.sleep(.5)
        else:raise RuntimeError('Same release not ready: '+last_error)
        report['after_start']=after;report['phase']='OBSERVING_60_SECONDS';save()
        begin=time.monotonic();first=after;new_pid=after['pid']
        for index in range(13):
            h=health();verify()
            assert h['pid']==new_pid and h['worker_alive'] and h['identity_ready']
            assert prop(GUI,'MainPID')==gui_pid and prop('xserver-nodm.service','MainPID')==x_pid
            assert sha(PREF)==preference_sha and not h['schedule']['owner_fenced']
            report['samples'].append({'elapsed':time.monotonic()-begin,'detected_frames':h['detected_frames'],
                'face_processed':h['face_processed'],'optional':h['schedule']['optional'],
                'recovery':h['schedule']['yunet_recovery'],'primary_overruns':h['schedule']['primary_period_overruns']})
            save()
            if index<12:time.sleep(max(0,begin+(index+1)*5-time.monotonic()))
        final=health();elapsed=time.monotonic()-begin
        report.update(after=final,owners_after=owners(),ui_after=idle(),duration_seconds=elapsed,
            observed_yolo_hz=(final['detected_frames']-first['detected_frames'])/elapsed,
            observed_face_publish_hz=(final['face_processed']-first['face_processed'])/elapsed,
            counters_reset_by_one_explicit_restart=True,
            cross_restart_fault_total=3+final['schedule']['optional']['yunet']['overruns'])
        assert report['owners_after']==owner_locks()==[new_pid]
        report['passed']=(report['observed_yolo_hz']>=9.5 and final['face_backend']=='DPU_YUNET_INT8'
            and not final['schedule']['optional']['yunet']['disabled']
            and final['schedule']['optional']['yunet']['overruns']==0
            and final['schedule']['primary_period_overruns']==first['schedule']['primary_period_overruns'])
        report['phase']='RESTORED_SAME_RELEASE' if report['passed'] else 'RUNNING_WITH_RECORDED_LIMITATIONS'
    except Exception as exc:
        report['error']=type(exc).__name__+': '+str(exc);report['phase']='RECOVERY_ERROR'
        if stopped:
            try:report['fallback_start']=start_if_stopped()
            except Exception as recovery_error:report['fallback_error']=str(recovery_error)
    finally:
        if armed and prop(CAMERA,'ActiveState')=='active':
            command(['systemctl','stop',guard+'.timer']);report['guard_state']=prop(guard+'.timer','ActiveState')
        report['complete']=True;save()
    return report

args=sys.argv[1:];assert args in ([],['--run'],['--guard'])
if args==['--guard']:
    result=start_if_stopped();atomic(ROOT/'guard-result.json',result);print(json.dumps(result))
elif args==['--run']:print(json.dumps(run()))
else:
    assert not (ROOT/'report.json').exists()
    unit='aura-current-camera-recovery-'+ROOT.name
    command(['systemd-run','--unit='+unit,'--property=RuntimeMaxSec=150','/usr/bin/python3','-B',str(SOURCE),'--run'])
    print(json.dumps({'started':True,'unit':unit,'report':str(ROOT/'report.json')}))
