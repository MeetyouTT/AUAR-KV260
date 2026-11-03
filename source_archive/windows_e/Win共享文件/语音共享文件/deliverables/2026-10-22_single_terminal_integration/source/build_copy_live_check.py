"""One-line capture candidate, live UVC check, always restore the retained unit."""
import ast,hashlib,json
from pathlib import Path

root=Path(__file__).resolve().parent
library=Path('/home/ghmd/aura-sface-shadow-candidate-20261021/deploy-preparation/board_shadow_pilot.py')
assert hashlib.sha256(library.read_bytes()).hexdigest()=='4bbc86bff5ebd75842940da5b788a43467d54e3905cc95f666f5ae74b958bdb3'
prefix=library.read_text().split('\ndef main():',1)[0]
body=r'''
def main():
    assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()=='215c4292-ce84-4828-9827-83c32ba66564'
    assert digest(UNIT)==UNIT_SHA
    before=camera();healthy(before);single_owner(before['pid']);idle=ui_idle()
    assert before.get('shadow') is None
    original_config=BASE/'board_camera_ui.json';identity_path=BASE/'board_identity.json'
    assert runtime_for(before['pid'])==(BASE/'aura',original_config)
    for name,expected in BASELINE.items():assert digest(BASE/'aura'/name)==expected
    identity=json.loads(identity_path.read_text());assert identity['face_backend']['kind']=='dpu_yunet'
    assert identity['feature_backend']=={'kind':'windows_sface','host':'192.168.50.1','port':8792,'timeout_ms':650}
    for key in ('model','manifest'):assert digest(identity['face_backend'][key])==identity['face_backend'][key+'_sha256']
    for path in [identity['database']]+([identity['enrollment_photos']['directory']] if identity.get('enrollment_photos') else []):
        assert (BASE/'aura').resolve() not in Path(path).expanduser().resolve().parents
    usb=Path('/sys/bus/usb/devices/1-1.2')
    assert (usb/'idVendor').read_text().strip()=='17ef' and (usb/'idProduct').read_text().strip()=='a03b'
    assert (usb/'devnum').read_text().strip()=='4','Revalidate endpoint mapping before fixed-boot observation'
    original_unit=UNIT.read_bytes()
    protected={str(p):digest(p) for p in [original_config,identity_path,
        Path('/home/root/aura-speech-motion-20261021/de989bf024a9/startup/config.json'),
        Path('/home/root/.local/share/aura/handsfree_dialogue.json')]}
    unit_pids={name:service('show',name,'-p','MainPID','--value').strip()
        for name in ['aura-avatar-ui.service','xserver-nodm.service']}
    folder=Path('/home/root/aura-dpu-vision-20261021/capture-copy-live')/('d74e30250e945842-'+str(os.getpid()))
    folder.mkdir(parents=True,exist_ok=False);candidate=folder/'aura'
    shutil.copytree(BASE/'aura',candidate,ignore=shutil.ignore_patterns('__pycache__','*.sqlite*','*.db'))
    path=candidate/'board/vision/ui_camera_service.py'
    raw=path.read_text();old='image=np.frombuffer(data,dtype=np.uint8).reshape(h,w,3).copy()'
    new='image=np.frombuffer(data,dtype=np.uint8).reshape(h,w,3)'
    assert raw.count(old)==1
    raw=raw.replace(old,new,1);ast.parse(raw)
    assert hashlib.sha256(raw.encode()).hexdigest()=='d74e30250e94584217c90eba9efaed41413e72d64505eeecd20d7cce66e7de45'
    path.write_text(raw)
    updated=original_unit.decode().replace(str(BASE/'aura'),str(candidate)).encode()
    assert updated!=original_unit
    (folder/'camera.service.original').write_bytes(original_unit)
    (folder/'camera.service.candidate').write_bytes(updated)
    (folder/'rollback.py').write_text(rollback_source(folder))
    report={'scope':'SINGLE_COPY_REMOVAL_REAL_UVC_60S_ALWAYS_RESTORED',
        'passed':False,'complete':False,'phase':'BASELINE','root':str(folder),
        'camera_before':before,'ui_before':idle,'original_unit_sha256':UNIT_SHA,
        'candidate_ui_sha256':'d74e30250e94584217c90eba9efaed41413e72d64505eeecd20d7cce66e7de45',
        'original_runtime':str(BASE/'aura'),'candidate_runtime':str(candidate),
        'candidate_unit_sha256':hashlib.sha256(updated).hexdigest(),'samples':[],
        'identity_backend_changed':False,'identity_database_configuration_changed':False,
        'metrics_or_shadow_enabled':False,'requested_observation_s':60}
    def save():atomic(folder/'deployment-result.json',(json.dumps(report,indent=2)+'\n').encode())
    cursor=kernel_cursor();time.sleep(5)
    assert audio_warnings(cursor)==0,'USB baseline already warning; refuse live candidate'
    check=camera();healthy(check);assert check['pid']==before['pid']
    ui_idle();assert UNIT.read_bytes()==original_unit
    for p,expected in protected.items():assert digest(p)==expected
    timer='aura-capture-copy-live-rollback-'+str(os.getpid());report['timer']=timer
    command(['systemd-run','--unit='+timer,'--on-active=240s','/usr/bin/python3','-B',str(folder/'rollback.py')])
    armed=True
    try:
        service('stop','aura-camera-ui.service');assert UNIT.read_bytes()==original_unit
        atomic(UNIT,updated);service('daemon-reload');service('start','--no-block','aura-camera-ui.service')
        deadline=time.monotonic()+35
        while time.monotonic()<deadline:
            try:
                state=camera();report['latest_camera_seen']=state;healthy(state)
                if runtime_for(state['pid'])==(candidate,original_config):break
            except Exception:pass
            time.sleep(.4)
        else:raise RuntimeError('Capture candidate did not become ready')
        single_owner(state['pid']);first=state;started=time.monotonic();first_cpu=cpu()
        report['phase']='OBSERVING';report['candidate_camera_pid']=state['pid'];save()
        for index in range(13):
            state=camera();report['latest_camera_seen']=state;healthy(state)
            assert state['pid']==first['pid'] and state.get('shadow') is None
            state['elapsed_s']=time.monotonic()-started;report['samples'].append(state)
            assert audio_warnings(cursor)==0,'USB warning during copy-only candidate'
            for name,pid in unit_pids.items():assert service('show',name,'-p','MainPID','--value').strip()==pid
            report['elapsed_s']=state['elapsed_s'];save()
            if index<12:time.sleep(max(0,started+(index+1)*5-time.monotonic()))
        elapsed=time.monotonic()-started
        report['camera_after']=state;report['observed_seconds']=elapsed
        report['observed_yolo_hz']=(state['detected_frames']-first['detected_frames'])/elapsed
        report['observed_capture_hz']=(state['capture_frames']-first['capture_frames'])/elapsed
        report['cpu_window']=cpu_delta(first_cpu,cpu())
        assert elapsed>=60 and report['observed_yolo_hz']>=9
        for p,expected in protected.items():assert digest(p)==expected
        assert digest(path)==report['candidate_ui_sha256']
        report['usb_warning_count']=audio_warnings(cursor);assert report['usb_warning_count']==0
        report['passed']=True;report['observation_status']='LIVE_CAMERA_SHORT_WINDOW_PASSED_NOT_LONG_STABILITY_OR_GAIN_COMPARISON'
    except Exception as exc:
        report['error']=type(exc).__name__+': '+str(exc)[:500]
        report['observation_status']='FAILED'
    finally:
        report['phase']='RESTORING';save()
        try:
            report['rollback_output']=command(['/usr/bin/python3','-B',str(folder/'rollback.py')],timeout=70)[-500:]
            deadline=time.monotonic()+35
            while time.monotonic()<deadline:
                try:
                    restored=camera();report['latest_restored_seen']=restored;healthy(restored)
                    if runtime_for(restored['pid'])==(BASE/'aura',original_config):break
                except Exception:pass
                time.sleep(.4)
            else:raise RuntimeError('Original retained camera did not recover')
            assert UNIT.read_bytes()==original_unit and restored.get('shadow') is None
            single_owner(restored['pid'])
            for name,expected in BASELINE.items():assert digest(BASE/'aura'/name)==expected
            for p,expected in protected.items():assert digest(p)==expected
            for name,pid in unit_pids.items():assert service('show',name,'-p','MainPID','--value').strip()==pid
            report['restored']=restored;report['rollback_verified']=True
            service('stop',timer+'.timer');armed=False
        except Exception as exc:
            report['rollback_verified']=False;report['passed']=False
            report['rollback_error']=type(exc).__name__+': '+str(exc)[:500]
        report['rollback_timer_left_armed']=armed;report['protected_unit_pids']=unit_pids
        report['complete']=True;report['phase']='FINISHED';save()
    print(json.dumps({'root':str(folder),'passed':report['passed'],'complete':True,
        'rollback_verified':report['rollback_verified']}),flush=True)

if __name__=='__main__':
    import sys
    source=Path(sys._getframe().f_code.co_filename).resolve();key=digest(source)[:16]
    launch=Path('/home/root/aura-dpu-vision-20261021/capture-copy-launches')/key
    launch.mkdir(parents=True,exist_ok=True)
    if os.environ.get('AURA_RUN_CAPTURE_COPY_LIVE')=='1':
        try:
            main();result={'finished':True,'scope':'Read capture-copy-live deployment-result for outcome and restoration'}
        except Exception as exc:result={'finished':True,'error':type(exc).__name__+': '+str(exc)[:500]}
        (launch/'launch-result.json').write_text(json.dumps(result,indent=2)+'\n')
    else:
        assert not (launch/'launch-result.json').exists()
        unit='aura-capture-copy-live-'+key
        command(['systemd-run','--unit='+unit,'--property=RuntimeMaxSec=210',
            '--setenv=AURA_RUN_CAPTURE_COPY_LIVE=1','/usr/bin/python3','-B',str(source)])
        print(json.dumps({'started':True,'unit':unit,'launch_result':str(launch/'launch-result.json')}),flush=True)
'''
source=prefix+'\n'+body;ast.parse(source)
out=Path('/home/ghmd/aura-identity-dpu-check-20261018/board_capture_copy_live_20261022.py')
if out.exists():assert out.read_text()==source
else:out.write_text(source)
print(json.dumps({'source':str(out),'sha256':hashlib.sha256(out.read_bytes()).hexdigest(),'bytes':out.stat().st_size}))
