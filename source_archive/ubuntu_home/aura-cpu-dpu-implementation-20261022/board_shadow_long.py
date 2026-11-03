"""Long shadow validation. Prefix with the pinned reviewed pilot library to deploy.

This uses the existing six-file shadow overlay, never the new calibration code.
The only production change is an isolated camera unit, always reverted.
"""
import math


def process_cpu(pid):
    raw=(Path('/proc')/str(pid)/'stat').read_text().rsplit(') ',1)[1].split()
    return {'pid':pid,'ticks':int(raw[11])+int(raw[12]),'start_ticks':int(raw[19]),
            'rss_pages':int(raw[21]),'threads':int(raw[17])}


def measured_cpu(pid):
    value=cpu();value['camera']=process_cpu(pid)
    return value


def measured_delta(first,last):
    value=cpu_delta(first,last);a=first['camera'];b=last['camera']
    assert a['pid']==b['pid'] and a['start_ticks']==b['start_ticks'],'Process changed within CPU window'
    core_seconds=(b['ticks']-a['ticks'])/os.sysconf('SC_CLK_TCK')
    value.update(camera_core_seconds=core_seconds,
        camera_percent_of_board=100*core_seconds/value['duration_s']/os.cpu_count(),
        cpu_count=os.cpu_count(),camera_rss_bytes=b['rss_pages']*os.sysconf('SC_PAGE_SIZE'),
        camera_threads=b['threads'])
    return value


def coverage(samples):
    # A conservative, explicitly sampled estimate, not continuous presence truth.
    seconds=0.;completed=0;accepted=0;yunet=0
    for a,b in zip(samples,samples[1:]):
        if a['face_count']==b['face_count']==1:
            seconds+=b['elapsed_s']-a['elapsed_s']
            completed+=b['shadow']['execution']['completed']-a['shadow']['execution']['completed']
            accepted+=b['shadow']['accepted']-a['shadow']['accepted']
            yunet+=b['dpu_schedule']['optional']['yunet']['calls']-a['dpu_schedule']['optional']['yunet']['calls']
    return {'scope':'5-second intervals with one face at BOTH endpoints; sampled estimate, not continuous coverage',
        'sampled_single_face_seconds':seconds,'sface_completed_in_covered_intervals':completed,
        'sface_accepted_in_covered_intervals':accepted,
        'sface_accepted_hz_in_covered_intervals':accepted/seconds if seconds else None,
        'yunet_hz_in_covered_intervals':yunet/seconds if seconds else None}


def validate_observation(report):
    state=report['camera_after'];shadow=state['shadow'];first=report['samples'][0]
    elapsed=report['observation_elapsed_s']
    yolo=(state['detected_frames']-first['detected_frames'])/elapsed
    yunet=(state['dpu_schedule']['optional']['yunet']['calls']-first['dpu_schedule']['optional']['yunet']['calls'])/elapsed
    complete=shadow['execution']['completed']-first['shadow']['execution']['completed']
    accepted=shadow['accepted']-first['shadow']['accepted']
    cov=coverage(report['samples'])
    report.update(observed_yolo_hz=yolo,observed_yunet_hz=yunet,
        shadow_completed=complete,shadow_accepted=accepted,face_coverage=cov)
    insufficient=[];failures=[]
    if complete<100 or accepted<100:insufficient.append('Fewer than100 actual and target/freshness-accepted SFace completions')
    if cov['sampled_single_face_seconds']<=0:insufficient.append('No single-face intervals at both sampled endpoints')
    if yolo<max(9.,report['baseline_observed_yolo_hz']*.95):failures.append('Primary throughput below preregistered gate')
    if cov['sampled_single_face_seconds']>0:
        if cov['sface_accepted_hz_in_covered_intervals']<.5:failures.append('SFace valid completion rate below0.5Hz in sampled covered intervals')
        if cov['yunet_hz_in_covered_intervals']<1.5:failures.append('YuNet rate below1.5Hz in sampled covered intervals')
    if elapsed<1800:failures.append('Observation shorter than1800s')
    if report['usb_audio_warning_count']!=0:failures.append('USB audio warning')
    if shadow['same_crop_cosine']['count']!=0 or shadow['templates_written'] or shadow['identity_decisions_from_shadow']:
        failures.append('Unexpected identity output or cosine mode')
    if shadow['failures']:failures.append('Shadow computation failure')
    report['stale_results_rejected']=shadow['stale']
    report['coverage_insufficiencies']=insufficient;report['gate_failures']=failures
    report['observation_status']='FAILED' if failures else 'INSUFFICIENT_FACE_COVERAGE' if insufficient else 'PASSED'
    report['passed']=not failures and not insufficient


def main():
    assert os.uname().machine=='aarch64'
    assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()=='215c4292-ce84-4828-9827-83c32ba66564'
    patch=Path('/home/root/aura-dpu-vision-20261021/staging/d6f06aa970649c9e/bundle.tar.gz')
    patch_sha='d6f06aa970649c9e076ccc916ca0c5c3257dcf79639082dd026fa7e90fed95bc'
    model=Path('/home/root/aura-dpu-vision-20261021/staging/03580d3216661ba0/kit/sface_public_int8.xmodel')
    manifest_path=model.with_name('sface-manifest.json')
    manifest_sha='d52e4343910f7d3c775405c161e3fdf16db27396891dc617b0e5defdb878841b'
    assert digest(patch)==patch_sha and digest(model)==MODEL_SHA and digest(manifest_path)==manifest_sha
    assert digest(UNIT)==UNIT_SHA,'Baseline unit changed'
    before=camera();healthy(before);single_owner(before['pid']);idle=ui_idle()
    config_path=BASE/'board_camera_ui.json';identity_path=BASE/'board_identity.json'
    assert runtime_for(before['pid'])==(BASE/'aura',config_path)
    config=json.loads(config_path.read_text());identity=json.loads(identity_path.read_text())
    assert Path(config['identity']['config'])==identity_path and identity['face_backend']['kind']=='dpu_yunet'
    assert identity['feature_backend']=={'kind':'windows_sface','host':'192.168.50.1','port':8792,'timeout_ms':650}
    assert identity['model_id']=='sface-2021dec-0ba9fbfa01b5' and 'dpu_sface_shadow' not in identity
    for rel,sha in BASELINE.items():assert digest(BASE/'aura'/rel)==sha
    for key in ('model','manifest'):assert digest(identity['face_backend'][key])==identity['face_backend'][key+'_sha256']
    for private in [identity['database']]+([identity['enrollment_photos']['directory']] if identity.get('enrollment_photos') else []):
        assert (BASE/'aura').resolve() not in Path(private).expanduser().resolve().parents
    original=UNIT.read_bytes()
    ui_pid=service('show','aura-avatar-ui.service','-p','MainPID','--value').strip()
    xserver_pid=service('show','xserver-nodm.service','-p','MainPID','--value').strip()
    protected_paths=[config_path,identity_path]
    for unit_name in ['aura-avatar-ui.service','xserver-nodm.service']:
        path=Path(service('show',unit_name,'-p','FragmentPath','--value').strip())
        assert path.is_absolute() and path.is_file(),'Missing actual service fragment: '+unit_name
        protected_paths.append(path)
    protected={str(p):digest(p) for p in protected_paths}
    root=Path('/home/root/aura-dpu-vision-20261021/shadow-long')/(patch_sha[:16]+'-'+str(os.getpid()))
    root.mkdir(parents=True,exist_ok=False);candidate=root/'aura'
    with tarfile.open(patch) as archive:
        meta=json.load(archive.extractfile('patch-manifest.json'))
        assert meta['baseline']==BASELINE and set(meta['files'])==set(OVERLAY)
        assert set(archive.getnames())==set(OVERLAY)|{'patch-manifest.json'}
        data={}
        for rel,sha in OVERLAY.items():
            item=archive.getmember(rel);assert item.isfile() and item.size<=131072
            raw=archive.extractfile(item).read()
            assert hashlib.sha256(raw).hexdigest()==sha==meta['files'][rel]['sha256'] and len(raw)==meta['files'][rel]['bytes']
            ast.parse(raw.decode(),filename=rel);data[rel]=raw
    shutil.copytree(BASE/'aura',candidate,ignore=shutil.ignore_patterns('__pycache__','*.sqlite*','*.db'))
    for rel,raw in data.items():
        path=candidate/rel;assert not path.is_symlink();path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(raw)
    saved=json.loads(json.dumps(identity))
    identity['dpu_sface_shadow']={'enabled':True,'model':str(model),'manifest':str(manifest_path),
        'model_sha256':MODEL_SHA,'manifest_sha256':manifest_sha,'max_source_age_ms':1000,
        'interval_ms':1000,'compare_cosine':False}
    assert {k:v for k,v in identity.items() if k!='dpu_sface_shadow'}==saved
    new_identity=root/'board_identity.json';new_identity.write_text(json.dumps(identity,indent=2)+'\n')
    config['identity']['config']=str(new_identity)
    new_config=root/'board_camera_ui.json';new_config.write_text(json.dumps(config,indent=2)+'\n')
    old=original.decode();assert old.count(str(BASE/'aura'))>=1 and old.count(str(config_path))>=1
    new=old.replace(str(BASE/'aura'),str(candidate)).replace(str(config_path),str(new_config)).encode()
    (root/'camera.service.original').write_bytes(original);(root/'camera.service.candidate').write_bytes(new)
    (root/'rollback.py').write_text(rollback_source(root))
    report={'scope':'REAL_FACE_THREE_MODEL_SHADOW_1800S_ALWAYS_RESTORED',
        'passed':False,'complete':False,'phase':'BASELINE','root':str(root),'baseline_runtime':str(BASE/'aura'),
        'baseline_unit_sha256':UNIT_SHA,'boot_id':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
        'patch_sha256':patch_sha,'samples':[],'camera_before':before,'ui_before':idle,
        'identity_backend_changed':False,'identity_database_configuration_changed':False,'compare_cosine':False,
        'ui_pid_before':ui_pid,'xserver_pid_before':xserver_pid,
        'measurement_scope':'5-second health snapshots and /proc CPU deltas; no new per-stage instrumentation; no XRT collection owned by this script',
        'preregistered_gates':{'seconds':1800,'actual_and_accepted_sface_minimum':100,'yolo_min_hz':9.,
            'yolo_min_fraction_of_baseline':.95,'sampled_single_face_sface_min_hz':.5,'sampled_single_face_yunet_min_hz':1.5}}
    baseline_initial=camera();baseline_cursor=kernel_cursor()
    baseline_first=measured_cpu(before['pid']);time.sleep(15);baseline_last=measured_cpu(before['pid'])
    baseline_after=camera();healthy(baseline_after)
    assert audio_warnings(baseline_cursor)==0,'USB audio already warning in baseline; refuse candidate'
    report['baseline_cpu']=measured_delta(baseline_first,baseline_last)
    report['baseline_observed_yolo_hz']=(baseline_after['detected_frames']-baseline_initial['detected_frames'])/report['baseline_cpu']['duration_s']
    ui_idle();assert UNIT.read_bytes()==original
    for p,sha in protected.items():assert digest(p)==sha
    cursor=kernel_cursor();timer='aura-sface-shadow-rollback-'+str(os.getpid());report['timer']=timer
    command(['systemd-run','--unit='+timer,'--on-active=2220s','/usr/bin/python3','-B',str(root/'rollback.py')])
    armed=True
    try:
        service('stop','aura-camera-ui.service');assert UNIT.read_bytes()==original
        atomic(UNIT,new);service('daemon-reload');service('start','--no-block','aura-camera-ui.service')
        deadline=time.monotonic()+35
        while time.monotonic()<deadline:
            try:
                state=camera();healthy(state,True)
                if runtime_for(state['pid'])==(candidate,new_config):break
            except Exception:pass
            time.sleep(.4)
        else:raise RuntimeError('Shadow startup timeout')
        single_owner(state['pid']);started=time.monotonic();cpus=[measured_cpu(state['pid'])]
        report['phase']='OBSERVING';report['camera_pid']=state['pid']
        for index in range(361):
            state=camera();report['latest_camera_seen']=state;healthy(state,True)
            assert state['pid']==report['camera_pid'],'Camera process changed'
            state['face_count']=face_count();state['elapsed_s']=time.monotonic()-started
            current_cpu=measured_cpu(state['pid']);state['cpu_window']=measured_delta(cpus[-1],current_cpu) if index else None
            cpus.append(current_cpu);report['samples'].append(state)
            report['elapsed_s']=state['elapsed_s'];report['last_shadow_completed']=state['shadow']['execution']['completed']
            if index%6==0 or index==360:
                assert audio_warnings(cursor)==0,'USB audio warnings returned'
                assert ui_pid==service('show','aura-avatar-ui.service','-p','MainPID','--value').strip(),'UI process changed'
                assert xserver_pid==service('show','xserver-nodm.service','-p','MainPID','--value').strip(),'Xserver process changed'
                write_report(root,report)
            if index<360:time.sleep(max(0,started+(index+1)*5-time.monotonic()))
        report['camera_after']=state;report['observation_elapsed_s']=time.monotonic()-started
        report['pilot_cpu_total']=measured_delta(cpus[0],cpus[-1]);report['usb_audio_warning_count']=audio_warnings(cursor)
        validate_observation(report)
        for p,sha in protected.items():assert digest(p)==sha
        report['phase']='RESTORING'
    except Exception as exc:
        report['error']=type(exc).__name__+': '+str(exc)[:500];report['observation_status']='FAILED'
    finally:
        write_report(root,report)
        try:
            report['rollback_output']=command(['/usr/bin/python3','-B',str(root/'rollback.py')],timeout=70)[-500:]
            deadline=time.monotonic()+30
            while time.monotonic()<deadline:
                try:
                    restored=camera();healthy(restored)
                    if runtime_for(restored['pid'])==(BASE/'aura',config_path):break
                except Exception:pass
                time.sleep(.4)
            else:raise RuntimeError('YuNet restoration unavailable')
            assert UNIT.read_bytes()==original and not restored.get('shadow')
            single_owner(restored['pid'])
            for p,sha in protected.items():assert digest(p)==sha
            for rel,sha in BASELINE.items():assert digest(BASE/'aura'/rel)==sha
            report['restored']=restored;report['rollback_verified']=True
            service('stop',timer+'.timer');armed=False
        except Exception as exc:
            report['rollback_error']=type(exc).__name__+': '+str(exc)[:500]
            report['rollback_verified']=False;report['passed']=False
        report['rollback_timer_left_armed']=armed
        report['ui_pid_preserved']=ui_pid==service('show','aura-avatar-ui.service','-p','MainPID','--value').strip()
        report['xserver_pid_preserved']=xserver_pid==service('show','xserver-nodm.service','-p','MainPID','--value').strip()
        report['complete']=True;report['phase']='FINISHED';write_report(root,report)
    print(json.dumps({'root':str(root),'passed':report['passed'],'complete':True,
        'status':report.get('observation_status'),'rollback_verified':report['rollback_verified']}),flush=True)
