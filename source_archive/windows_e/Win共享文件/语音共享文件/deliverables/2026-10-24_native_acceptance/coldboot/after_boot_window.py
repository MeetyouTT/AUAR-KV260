"""Read-only validation after a human-confirmed physical power cycle."""
import hashlib,json,os,subprocess,sys,time,urllib.request
from pathlib import Path

source=Path(__file__).resolve();token=hashlib.sha256(source.read_bytes()).hexdigest()[:16]
root=Path('/home/root/aura-native-coldboot-20261024/verification')/token
root.mkdir(parents=True,exist_ok=True,mode=0o700)
BOOT='b7871498-884a-4190-8ba1-6876a63a3f6c'
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==BOOT
if sys.argv[1:]!=['--worker']:
    assert not sys.argv[1:] and not (root/'started.json').exists()
    (root/'started.json').write_text(json.dumps({'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),
        'scope':'human confirmed unplug/replug after normal OS shutdown; read-only startup window'})+'\n')
    p=subprocess.run(['systemd-run','--no-block','--quiet','--unit=aura-cold-window-'+token,
        '--property=Type=oneshot','--property=RuntimeMaxSec=90','--property=Nice=19',
        '/usr/bin/python3','-B',str(source),'--worker'],capture_output=True,text=True,timeout=8)
    assert p.returncode==0,p.stderr
    print(json.dumps({'started':True,'root':str(root),'seconds':60,'no_mutation':True}))
    raise SystemExit(0)

op=urllib.request.build_opener(urllib.request.ProxyHandler({}))
def get(port,path):
    with op.open('http://127.0.0.1:'+str(port)+path,timeout=4) as stream:return json.load(stream)
def counters(h):
    s=h['dpu_schedule'];identity=h['identity'];face=identity['face_targets']
    return dict(pid=h['pid'],frames=h['detected_frames'],primary_overruns=s['primary_period_overruns'],
        optional_overruns={k:s['optional'][k]['overruns'] for k in ['yunet','sface']},
        optional_completed={k:s['optional'][k]['native_completed'] for k in ['yunet','sface']},
        sface_completed=identity['feature_inference']['completed'],gaps=face['freshness_metrics']['counters']['observed_gap_intervals'])
report={'scope':'PHYSICAL_POWER_CYCLE_AND_60_SECONDS_POST_BOOT_BUSINESS',
    'current_boot':BOOT,'human_reported_power_reconnected':True,'no_mutation':True,'samples':[],'passed':False}
try:
    shutdown=json.loads(Path('/home/root/aura-native-coldboot-20261024/c6b338dc8423086d/shutdown.json').read_text())
    assert shutdown['safe_to_disconnect_power'] and shutdown['poweroff_scheduled'] and not shutdown.get('failure')
    seed=shutdown['checkpoint']['seed'];assert seed['boot_id']!=BOOT and not seed['fenced']
    report['previous_boot']=seed['boot_id'];report['shutdown_confirmed']=True
    report['old_kernel_final_counters']={k:seed[k] for k in ['primary_calls','primary_period_overruns','admissions','overruns','completed','native_failures','not_submitted','recovery']}
    report['old_kernel_runtime_seconds']=seed['captured_mono_ns']/1e9-seed['source_birth_ticks']/os.sysconf('SC_CLK_TCK')
    h=get(8790,'/health');before=counters(h);report['before']=before
    handoff=h['dpu_schedule']['protection_handoff'];assert handoff['mode']=='native_new_kernel_boot'
    assert handoff['source_boot']==seed['boot_id'] and handoff['current_boot']==BOOT
    prior=handoff['previous_kernel_counters'];assert prior['overruns']==seed['overruns'] and not prior['history_is_lower_bound']
    assert prior['sface_counters']==shutdown['checkpoint']['auxiliary']['sface_counters']
    archive=Path(handoff['archive_path']);assert hashlib.sha256(archive.read_bytes()).hexdigest()==handoff['archive_sha256']
    assert json.loads(archive.read_text())['checkpoint']==shutdown['checkpoint']
    report['archive_sha256']=handoff['archive_sha256'];report['counter_history_preserved']=True
    meta=json.loads(Path('/home/root/aura-native-live-20261024/ops/be72669aa53de735/meta.json').read_text())
    cfg=json.loads(Path(meta['candidate_config']).read_text());identity_path=Path(cfg['identity']['config'])
    identity=json.loads(identity_path.read_text());db=Path(identity['database'])
    report['identity_config_sha256']=hashlib.sha256(identity_path.read_bytes()).hexdigest()
    report['database_sha256_before']=hashlib.sha256(db.read_bytes()).hexdigest()
    assert report['identity_config_sha256']=='398ece6a4d5d81076c9a4f9f40a43e97cedd469e0b47e3a835e589a2255ca6e3'
    assert report['database_sha256_before']=='ee22b97dbaa6f29f5b76c18565acc4f597cd61c6090f1946b993d2a29ab8101a'
    began=time.monotonic();next_at=began
    while time.monotonic()-began<60:
        time.sleep(max(0,next_at-time.monotonic()));next_at+=2
        h=get(8790,'/health');s=h['dpu_schedule'];i=h['identity'];face=i['face_targets']
        assert h['pid']==before['pid'] and not s['owner_fenced'] and s['native_abi']==2
        assert not h['camera_error'] and not h['detector_error'] and i['ready']
        assert face['backend']=='DPU_YUNET_INT8' and face['worker_alive']
        item=counters(h);item['elapsed_seconds']=time.monotonic()-began;report['samples'].append(item)
    after=counters(get(8790,'/health'));seconds=time.monotonic()-began;report['after']=after
    report['duration_seconds']=seconds;report['yolo_hz']=(after['frames']-before['frames'])/seconds
    report['new_primary_overruns']=after['primary_overruns']-before['primary_overruns']
    report['new_optional_overruns']={k:after['optional_overruns'][k]-before['optional_overruns'][k] for k in before['optional_overruns']}
    report['new_gaps']=after['gaps']-before['gaps'];report['new_sface_completed']=after['sface_completed']-before['sface_completed']
    report['database_sha256_after']=hashlib.sha256(db.read_bytes()).hexdigest()
    services={}
    for unit in ['aura-camera-ui.service','aura-avatar-ui.service','xserver-nodm.service']:
        p=subprocess.check_output(['systemctl','show',unit,'-p','ActiveState','-p','MainPID','-p','NRestarts'],text=True)
        services[unit]=dict(row.split('=',1) for row in p.splitlines() if '=' in row)
    report['services']=services
    gui=get(8783,'/api/state');report['gui']={k:gui.get(k) for k in ['phase','audio_output_state','ui_page','playing','paused','backend']}
    report['passed']=report['yolo_hz']>=9.5 and not report['new_primary_overruns'] and not report['new_gaps'] \
        and not any(report['new_optional_overruns'].values()) and all(v['ActiveState']=='active' for v in services.values()) \
        and report['database_sha256_after']==report['database_sha256_before']
except BaseException as exc:report['failure']=type(exc).__name__+': '+str(exc)
finally:
    with (root/'report.json').open('x') as out:json.dump(report,out,indent=2);out.write('\n')
    print(json.dumps({'report_path':str(root/'report.json'),'passed':report['passed'],'failure':report.get('failure')}))
