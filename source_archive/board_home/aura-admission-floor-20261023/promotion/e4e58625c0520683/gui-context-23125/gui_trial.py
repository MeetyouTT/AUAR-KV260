"""GUI-only lifecycle correction with owned rollback; camera/model state stays live."""
import fcntl,hashlib,importlib.util,json,os,shutil,subprocess,sys,time,traceback,urllib.request
from pathlib import Path

BOOT='008f3e1b-c627-4b98-b120-d2a460cdbcbe'
UNIT=Path('/etc/systemd/system/aura-camera-ui.service')
UNIT_SHA='29786434df9bb9b94a8e640a7a48db47019c224d3876037ce27d3467bb2f5512'
BASE=Path('/home/root/aura-dpu-vision-20261021/postpower-retry-live/release-reliability-f7624754038f-450136/gui-runtime')
PREF=Path('/home/root/.local/share/aura/handsfree_dialogue.json')
GUI='aura-avatar-ui.service';CAMERA='aura-camera-ui.service'
DEFINITIONS=Path('/home/root/aura-post-power-20261022/helpers/10261c1b5b2b7458/source.py')
DEFINITION_SHA='10261c1b5b2b745877121c90d940be80e67f91ae57a524ed2040a1f52af4f65c'
op=urllib.request.build_opener(urllib.request.ProxyHandler({}))
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def command(args,timeout=20):return subprocess.check_output(args,timeout=timeout,stderr=subprocess.STDOUT,text=True).strip()
def prop(unit,key):return command(['systemctl','show',unit,'-p',key,'--value'])
def get(port,path):
    with op.open('http://127.0.0.1:'+str(port)+path,timeout=4) as r:return json.load(r)
def ui():return get(8783,'/api/state')
def camera():
    h=get(8790,'/health');f=h['identity']['face_targets'];s=h['dpu_schedule']
    return {'pid':h['pid'],'detected_frames':h['detected_frames'],'detection_hz':h['detection_hz'],
        'identity_ready':h['identity']['ready'],'feature_inference':h['identity']['feature_inference'],
        'face_processed':f['processed'],'worker_alive':f['worker_alive'],'worker_faults':f['worker_faults'],
        'face_backend':f['backend'],'gaps':f['freshness_metrics']['counters']['observed_gap_intervals'],
        'process_errors':f['freshness_metrics']['counters']['process_errors'],
        'optional':s['optional'],'recovery':s['yunet_recovery'],'primary_overruns':s['primary_period_overruns'],
        'owner_fenced':s['owner_fenced'],'diagnostic_failures':s['diagnostic_failures'],
        'fault_events':s['optional_diagnostics']['fault_events']}
def validate_preserved_camera(h):
    assert h['worker_alive'] and h['identity_ready'] and not h['owner_fenced']
    assert not h['worker_faults'] and not h['diagnostic_failures']
    assert type(h['gaps']) is int and h['gaps']>=0
    assert h['feature_inference']['ready']
    jobs=h['optional'];yunet=jobs['yunet']
    if yunet.get('disabled'):
        assert h['face_backend']=='CPU_YUNET_FALLBACK_AFTER_DPU_OVERRUN'
        assert h['recovery']['phase']=='LATCHED'
        events=[e for e in h['fault_events'] if e['task_code']==1]
        assert type(yunet.get('overruns')) is int and yunet['overruns']>0
        assert len(events)==yunet['overruns'] and len({e['event_sequence'] for e in events})==len(events)
        assert all(e['native_completed']==1 and e['native_status']==0 and not e['native_failed']
                   and not e['body_failed'] for e in events)
    else:
        assert h['face_backend']=='DPU_YUNET_INT8' and h['recovery']['phase']=='RUNNING'
    assert not jobs.get('sface',{}).get('disabled')
def assert_camera_unchanged(before,after):
    validate_preserved_camera(after)
    assert after['pid']==before['pid'] and after['face_backend']==before['face_backend']
    for kind in set(before['optional'])|set(after['optional']):
        a=before['optional'].get(kind,{});b=after['optional'].get(kind,{})
        assert b.get('disabled',False)==a.get('disabled',False) and b.get('overruns',0)==a.get('overruns',0)
    assert after['gaps']==before['gaps'],'Camera freshness gaps changed during GUI-only trial'
    assert after['primary_overruns']==before['primary_overruns'] and not after['process_errors']
def atomic(path,value):
    temp=path.with_name(path.name+'.tmp-'+str(os.getpid()))
    with temp.open('x') as f:json.dump(value,f,indent=2);f.write('\n');f.flush();os.fsync(f.fileno())
    os.replace(temp,path)
def drops():return {str(p):sha(p) for p in Path('/etc/systemd/system/aura-avatar-ui.service.d').glob('*.conf')}
def gui_command():
    return (Path('/proc')/prop(GUI,'MainPID')/'cmdline').read_bytes().split(b'\0')[:-1]
def retained():
    assert sha(DEFINITIONS)==DEFINITION_SHA
    spec=importlib.util.spec_from_file_location('_video_trial_retained',DEFINITIONS)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module
def idle():
    s=ui();assert s['phase']=='IDLE' and s['audio_output_state']=='IDLE_READY'
    assert not s.get('playing') and not s.get('paused') and s.get('pending_job') is None
    assert s.get('local_recording',{}).get('state')=='IDLE'
    assert not s.get('handsfree_dialogue',{}).get('microphone_open')
    assert not s.get('local_transcription',{}).get('service',{}).get('pending')
    pan=s.get('manual_pan',{});assert not pan.get('automatic_following') and pan.get('pulse_us') is None
    return s
def set_page(page):
    req=urllib.request.Request('http://127.0.0.1:8783/api/command',data=json.dumps({'type':'ui_page','page':page}).encode(),
        headers={'Content-Type':'application/json','Origin':'http://127.0.0.1:8783'})
    with op.open(req,timeout=5) as r:assert json.load(r)['ok']
    deadline=time.monotonic()+4
    while time.monotonic()<deadline:
        if ui()['ui_page']==page:return
        time.sleep(.1)
    raise RuntimeError('Page command did not settle')
def verify(folder,meta):
    assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==BOOT
    assert sha(UNIT)==UNIT_SHA and int(prop(CAMERA,'MainPID'))==meta['camera_pid']
    assert prop(CAMERA,'ActiveState')=='active'
    assert prop('xserver-nodm.service','MainPID')==meta['xserver_pid']
    for path,digest in meta['protected'].items():assert sha(path)==digest,path
    allowed=dict(meta['dropins']);override=Path(meta['override'])
    if override.exists():allowed[str(override)]=meta['override_sha256']
    assert drops()==allowed,'GUI drop-in set changed outside this trial'
    assert sha(PREF) in meta['allowed_preference_hashes'],'Preference changed outside owned stop'
def pcm_closed():
    paths=[Path('/proc/asound/card1/pcm0p/sub0/status'),Path('/proc/asound/card1/pcm0c/sub0/status')]
    deadline=time.monotonic()+8
    while time.monotonic()<deadline:
        assert paths[0].exists(),'MCP01 playback device disappeared'
        if all(not p.exists() or p.read_text().strip()=='closed' for p in paths):return
        time.sleep(.2)
    raise RuntimeError('Owned GUI did not close PCM')
def stop_gui(folder,meta):
    verify(folder,meta)
    state=prop(GUI,'ActiveState')
    if state in ('active','activating','reloading'):
        try:idle()
        except Exception:
            assert meta.get('owned_starting'),'Active user operation; refusing GUI stop'
        command(['systemctl','stop',GUI],timeout=40)
    assert prop(GUI,'ActiveState') in ('inactive','failed')
    digest=sha(PREF)
    if digest not in meta['allowed_preference_hashes']:
        assert json.loads(PREF.read_text())==json.loads((folder/'preference.original').read_text()),'Preference semantics changed during GUI stop'
        meta['allowed_preference_hashes'].append(digest)
    meta['owned_starting']=False;atomic(folder/'session.json',meta);pcm_closed()
def start_gui(folder,meta):
    verify(folder,meta);assert prop(GUI,'ActiveState') in ('inactive','failed');pcm_closed()
    original=(folder/'preference.original').read_bytes()
    assert hashlib.sha256(original).hexdigest()==meta['preference_sha256']
    if PREF.read_bytes()!=original:
        temp=PREF.with_name(PREF.name+'.video-trial-'+str(os.getpid()));temp.write_bytes(original);os.replace(temp,PREF)
    meta['owned_starting']=True;atomic(folder/'session.json',meta)
    command(['systemctl','start','--no-block',GUI]);deadline=time.monotonic()+110;last=''
    while time.monotonic()<deadline:
        try:
            s=idle();assert not s.get('error')
            assert s.get('avatar_display',{}).get('received',0)>=8
            meta['owned_starting']=False;atomic(folder/'session.json',meta);return s
        except Exception as exc:last=type(exc).__name__+': '+str(exc);time.sleep(.5)
    raise RuntimeError('GUI not ready: '+last)
def restore(folder,mode='rollback'):
    folder=Path(folder)
    with (folder/'restore.lock').open('a+') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX);meta=json.loads((folder/'session.json').read_text());verify(folder,meta)
        override=Path(meta['override'])
        if mode=='check':return {'passed':True,'read_only':True,'override_present':override.exists(),
            'camera_pid':meta['camera_pid'],'gui_pid':prop(GUI,'MainPID')}
        if meta.get('restored_to_original'):return {'restored':True,'already_restored':True,'camera_pid':meta['camera_pid'],'gui_pid':int(prop(GUI,'MainPID'))}
        if mode=='guard' and (folder/'accepted.json').exists() and not meta.get('manual_restore_in_progress'):
            return {'accepted':True,'no_action':True}
        if not meta.get('gui_transition_started'):
            idle();set_page(meta['original_page'])
            meta['restored_to_original']=True;atomic(folder/'session.json',meta)
            result={'restored':True,'page_only':True,'camera_pid':meta['camera_pid'],'gui_pid':int(prop(GUI,'MainPID'))}
            atomic(folder/'restore-result.json',result);return result
        if mode=='manual':
            idle();meta['manual_restore_in_progress']=True
            meta['manual_guard']='aura-video-manual-restore-'+folder.name+'-'+str(os.getpid())
            atomic(folder/'session.json',meta)
            command(['systemd-run','--unit='+meta['manual_guard'],'--on-active=120s','--property=RuntimeMaxSec=200',
                     '/usr/bin/python3','-B',str(folder/'restore_previous.py'),'--guard'])
            assert prop(meta['manual_guard']+'.timer','ActiveState')=='active'
        stop_gui(folder,meta)
        if override.exists():assert sha(override)==meta['override_sha256'];override.unlink()
        command(['systemctl','daemon-reload']);start_gui(folder,meta);set_page(meta['original_page']);verify(folder,meta)
        assert [part.decode() for part in gui_command()]==meta['original_command']
        result={'restored':True,'camera_pid':meta['camera_pid'],'gui_pid':int(prop(GUI,'MainPID'))}
        meta['restored_to_original']=True;meta['manual_restore_in_progress']=False;atomic(folder/'session.json',meta)
        if meta.get('manual_guard'):command(['systemctl','stop',meta['manual_guard']+'.timer'])
        atomic(folder/'restore-result.json',result);return result
def group_ticks(leader):
    procs={}
    for proc in Path('/proc').iterdir():
        if not proc.name.isdigit():continue
        try:
            f=(proc/'stat').read_text().rsplit(') ',1)[1].split();procs[int(proc.name)]=(int(f[1]),int(f[11])+int(f[12]))
        except (OSError,IndexError,ValueError):pass
    members={leader}
    while True:
        new=members|{pid for pid,(parent,_) in procs.items() if parent in members}
        if new==members:return {pid:procs[pid][1] for pid in members if pid in procs}
        members=new
def measure(folder,meta,label,page,duration=16):
    set_page(page);time.sleep(.6);before=ui();leader=int(prop(GUI,'MainPID'));ticks=group_ticks(leader)
    start=time.monotonic();start_ns=time.monotonic_ns();rows=[]
    while time.monotonic()-start<duration:
        s=idle();assert s['ui_page']==page and int(prop(GUI,'MainPID'))==leader
        assert not s.get('avatar_renderer',{}).get('presentation',{}).get('error')
        preview=s.get('ui_runtime',{}).get('preview_metrics') or {}
        rows.append({'elapsed':time.monotonic()-start,'preview':preview,'avatar':s['avatar_display']})
        time.sleep(min(2,max(0,duration-(time.monotonic()-start))))
    after=ui();elapsed=time.monotonic()-start;last=group_ticks(leader);assert last.keys()==ticks.keys()
    a=before['avatar_display'];b=after['avatar_display'];p0=before['ui_runtime']['preview_metrics'];p1=after['ui_runtime']['preview_metrics']
    return {'label':label,'page':page,'seconds':elapsed,'start_monotonic_ns':start_ns,'end_monotonic_ns':time.monotonic_ns(),'group_pids':sorted(last),
        'gui_group_one_core_percent':100*(sum(last.values())-sum(ticks.values()))/os.sysconf('SC_CLK_TCK')/elapsed,
        'avatar_hz':(b['received']-a['received'])/elapsed,'avatar_p95_ms':b['p95_ms'],
        'preview_frames_delta':p1['displayed_frames']-p0['displayed_frames'],
        'preview_hz':(p1['displayed_frames']-p0['displayed_frames'])/elapsed,
        'preview_after':p1,'samples':rows}
def clone(folder,pins):
    runtime=folder/'runtime'
    for p in (BASE/'aura').rglob('*.py'):
        if '__pycache__' not in p.parts:assert not p.is_symlink() and p.resolve()==p,'Linked Python source is not a writable clone input'
    before={str(p.relative_to(BASE/'aura')):sha(p) for p in (BASE/'aura').rglob('*.py') if '__pycache__' not in p.parts}
    shutil.copytree(BASE/'aura',runtime/'aura',symlinks=True,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
    for path in BASE.iterdir():
        if path.name in ('aura','managed-runs','launch.json','stage.log') or '.tmp-' in path.name:continue
        target=runtime/path.name
        if path.name.startswith('avatar') and path.name.endswith('settings.json'):shutil.copyfile(path,target)
        else:target.symlink_to(path.resolve(),target_is_directory=path.is_dir())
    for name,digest in pins.items():
        path=runtime/'aura'/name
        assert not path.is_symlink() and path.resolve()==path and runtime/'aura' in path.parents
        path.write_bytes((folder/'candidate/aura'/name).read_bytes());assert sha(path)==digest
    after={str(p.relative_to(runtime/'aura')):sha(p) for p in (runtime/'aura').rglob('*.py') if '__pycache__' not in p.parts}
    assert set(before)==set(after) and sorted(name for name in before if before[name]!=after[name])==sorted(pins)
    startup=folder/'startup';startup.mkdir();shutil.copyfile(BASE.parent/'gui-startup/launcher.py',startup/'launcher.py')
    cfg=json.loads((BASE.parent/'gui-startup/config.json').read_text());assert Path(cfg['runtime'])==BASE
    cfg['runtime']=str(runtime);cfg['component_sha256'].update(pins)
    (startup/'config.json').write_text(json.dumps(cfg,indent=2)+'\n')
    check=subprocess.run(['/usr/bin/python3','-B',str(startup/'launcher.py'),'--config',str(startup/'config.json'),'--preflight'],capture_output=True,text=True,timeout=20)
    assert check.returncode==0,check.stderr[-500:]+check.stdout[-500:]
    return runtime,startup,before,after
def run(folder,wrapper,pins):
    folder=Path(folder);wrapper=Path(wrapper);report={'complete':False,'accepted':False,'passed':False,'phase':'PREFLIGHT'}
    save=lambda:atomic(folder/'report.json',report)
    assert not (folder/'report.json').exists();save();meta=None;armed=False;mutated=False
    try:
        assert sha(UNIT)==UNIT_SHA and Path('/proc/sys/kernel/random/boot_id').read_text().strip()==BOOT
        m=retained();initial=idle();h=camera();report['camera_before_snapshot_mono_ns']=time.monotonic_ns()
        assert h['pid']==499773 and h['worker_alive'] and h['identity_ready']
        validate_preserved_camera(h)
        m.single_owner(h['pid']);assert initial['ui_page']=='vision'
        accepted=Path('/home/root/aura-vision-reliability-20261023/f7624754038f3669/report.json')
        assert sha(accepted)=='070ca6e5377a0c692cf4036b993963afd03e5e7cf49514932c5135aeb563085d'
        old=json.loads(accepted.read_text())
        identity_path=Path(old['identity_config']);database_path=Path(old['database'])
        assert sha(identity_path)==old['identity_config_sha256'] and sha(database_path)==old['database_sha256']
        assert sha(BASE/'aura/tools/libaura_pixels.so')=='201adac318e23411e608556fce360a335c422b129f64fa56e4d908ba39ab958f'
        baseline_pins=json.loads((folder/'baseline-pins.json').read_text())
        for name,digest in baseline_pins.items():assert sha(BASE/'aura'/name)==digest,name
        runtime,startup,before,after=clone(folder,pins)
        override=Path('/etc/systemd/system/aura-avatar-ui.service.d')/('zzzzzzzzzzzzz-aura-video-'+folder.name+'.conf')
        assert not override.exists();data=('[Service]\nExecStart=\nExecStart=/usr/bin/python3 -B '+str(startup/'launcher.py')+' --config '+str(startup/'config.json')+'\n').encode()
        (folder/'override.candidate').write_bytes(data);(folder/'preference.original').write_bytes(PREF.read_bytes())
        protected={str(p):sha(p) for p in (wrapper,folder/'gui_trial.py',identity_path,database_path,startup/'launcher.py',startup/'config.json',folder/'override.candidate',BASE.parent/'gui-startup/config.json')}
        protected.update({str(BASE/'aura'/name):digest for name,digest in baseline_pins.items()})
        protected.update({str(runtime/'aura'/name):sha(runtime/'aura'/name) for name in pins})
        meta={'camera_pid':h['pid'],'xserver_pid':prop('xserver-nodm.service','MainPID'),'dropins':drops(),
            'original_execstart':prop(GUI,'ExecStart'),'original_page':initial['ui_page'],
            'original_command':[part.decode() for part in gui_command()],
            'preference_sha256':sha(PREF),'allowed_preference_hashes':[sha(PREF)],'protected':protected,
            'override':str(override),'override_sha256':hashlib.sha256(data).hexdigest(),'owned_starting':False,
            'guard':'aura-video-restore-'+folder.name}
        atomic(folder/'session.json',meta);verify(folder,meta)
        rollback=folder/'restore_previous.py'
        rollback.write_text("import sys\nfrom pathlib import Path\nsys.dont_write_bytecode=True\nsys.path.insert(0,"+repr(str(folder))+")\nfrom gui_trial import restore\nargs=sys.argv[1:];assert args in ([],['--check'],['--restore'],['--guard'])\nprint(__import__('json').dumps(restore(Path("+repr(str(folder))+"),'check' if args in ([],['--check']) else 'guard' if args==['--guard'] else 'manual')))\n")
        meta['protected'][str(rollback)]=sha(rollback);atomic(folder/'session.json',meta)
        report.update(camera_before=h,original_gui_pid=int(prop(GUI,'MainPID')),runtime=str(runtime),startup=str(startup),
            candidate_pins=pins,gui_sources_before=before,gui_sources_after=after,rollback=str(rollback),phase='BASELINE')
        report['acceptance_scope']='GUI_LIFECYCLE_ONLY_EXISTING_CAMERA_FAULTS_PRESERVED'
        report['preserved_camera_degraded']=h['optional']['yunet'].get('disabled',False)
        command(['systemd-run','--unit='+meta['guard'],'--on-active=600s','--property=RuntimeMaxSec=200','/usr/bin/python3','-B',str(rollback),'--guard'])
        armed=True;assert prop(meta['guard']+'.timer','ActiveState')=='active'
        save();report['baseline_vision']=measure(folder,meta,'baseline_visible','vision')
        report['baseline_main']=measure(folder,meta,'baseline_hidden','main');set_page(meta['original_page']);save()
        idle();verify(folder,meta);m.single_owner(h['pid'])
        report['kernel_cursor_before_gui_stop']=m.kernel_cursor()
        report['phase']='SWITCHING_GUI_ONLY';save();mutated=True
        meta['gui_transition_started']=True;atomic(folder/'session.json',meta);stop_gui(folder,meta)
        override.write_bytes(data);command(['systemctl','daemon-reload']);start_gui(folder,meta);verify(folder,meta)
        assert str(startup/'launcher.py') in prop(GUI,'ExecStart')
        report['candidate_gui_pid']=int(prop(GUI,'MainPID'));report['phase']='TRIAL';save()
        report['trial_vision']=measure(folder,meta,'trial_visible','vision');save()
        report['trial_main']=measure(folder,meta,'trial_hidden','main');save()
        report['trial_remap']=measure(folder,meta,'trial_remap','vision');save()
        main=report['trial_main'];visible=report['trial_vision'];again=report['trial_remap'];baseline=report['baseline_main']
        assert main['preview_frames_delta']==0 and not main['preview_after']['sink_active']
        assert 'vision' not in main['preview_after']['active_outputs']
        for row in (visible,again):
            assert row['preview_hz']>=9.5 and row['preview_after']['frame_visible'] and row['preview_after']['sink_active']
            assert not row['preview_after']['error'] and row['preview_after']['entry_age_ms']['p95']<200
        for row in (main,visible,again):assert 7.5<=row['avatar_hz']<=8.5 and row['avatar_p95_ms']<=180
        reduction=1-main['gui_group_one_core_percent']/baseline['gui_group_one_core_percent']
        assert reduction>=.10,('GUI hidden-page CPU gate missed',reduction)
        final=camera();report['camera_after']=final;save();assert_camera_unchanged(h,final)
        report['new_usb_audio_warning_count']=m.audio_warnings(report['kernel_cursor_before_gui_stop'])
        assert report['new_usb_audio_warning_count']==0
        m.single_owner(h['pid']);verify(folder,meta);set_page(meta['original_page'])
        checked=restore(folder,'check');assert checked['passed']
        assert sha(PREF)==meta['preference_sha256']
        report.update(camera_after=final,hidden_page_gui_cpu_reduction_fraction=reduction,
            original_camera_unchanged=True,preference_unchanged=sha(PREF)==meta['preference_sha256'],
            rollback_check=checked,phase='ACCEPTED',accepted=True,passed=True)
        atomic(folder/'accepted.json',{'accepted':True,'pins':pins})
    except Exception as exc:
        report.update(error=type(exc).__name__+': '+str(exc),traceback=traceback.format_exc(),phase='REJECTED',accepted=False,passed=False)
        if meta:
            try:
                if mutated:report['restore']=restore(folder)
                else:set_page(meta['original_page']);report['page_restored']=True
            except Exception as restore_error:report['restore_error']=str(restore_error)
    finally:
        if armed and (report['accepted'] or report.get('restore',{}).get('restored') or report.get('page_restored')):
            command(['systemctl','stop',meta['guard']+'.timer']);report['guard_state']=prop(meta['guard']+'.timer','ActiveState')
        report['complete']=True;save()
    return report
