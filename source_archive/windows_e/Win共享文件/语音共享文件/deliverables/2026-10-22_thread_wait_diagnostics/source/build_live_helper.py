"""Always restore the retained dual-model camera after a 120-second probe."""
import ast,hashlib,json
from pathlib import Path

ROOT=Path(__file__).resolve().parent
meta=json.loads((ROOT/'live-bundle.json').read_text())
src=Path('/home/ghmd/aura-identity-dpu-check-20261018/board_capture_copy_live_20261022.py')
source=src.read_text()
def replace(old,new):
    global source
    assert source.count(old)==1,(old[:60],source.count(old))
    source=source.replace(old,new)
replace("'detection_hz','observation_age_ms','camera_error','detector_error','dpu_schedule')",
        "'detection_hz','observation_age_ms','camera_error','detector_error','dpu_schedule','pipeline_metrics')")
replace("folder=Path('/home/root/aura-dpu-vision-20261021/capture-copy-live')/('d74e30250e945842-'+str(os.getpid()))",
    "folder=Path('/home/root/aura-dpu-vision-20261021/thread-switch-live')/('"+meta['sha256'][:16]+"-'+str(os.getpid()))")
start=source.index("    path=candidate/'board/vision/ui_camera_service.py'",source.index('def main():'))
end=source.index('    assert updated!=original_unit',start)
body=r'''
    patch=Path('/home/root/aura-dpu-vision-20261021/staging')/BUNDLE_SHA[:16]/'bundle.tar.gz'
    assert digest(patch)==BUNDLE_SHA
    with tarfile.open(patch,'r:gz') as archive:
        manifest=json.load(archive.extractfile('candidate-manifest.json'))
        assert set(archive.getnames())==set(SOURCE_HASHES)|{'candidate-manifest.json'}
        for name,sha in SOURCE_HASHES.items():
            item=archive.getmember(name);assert item.isfile() and item.size<=65536
            data=archive.extractfile(item).read();assert hashlib.sha256(data).hexdigest()==sha
            assert sha==manifest['files'][name]['sha256'];ast.parse(data.decode())
            target=candidate/name;target.parent.mkdir(parents=True,exist_ok=True)
            assert not target.is_symlink();target.write_bytes(data)
    path=candidate/'board/vision/ui_camera_service.py'
    updated=original_unit.decode().replace(str(BASE/'aura'),str(candidate))
    assert updated.count('[Service]\n')==1
    updated=updated.replace('[Service]\n','[Service]\nEnvironment="AURA_PIPELINE_METRICS=1"\nEnvironment="AURA_DPU_DIAGNOSTICS=1"\nEnvironment="AURA_THREAD_SCHED_DIAGNOSTICS=switches"\n').encode()
'''
source=source[:start]+body+source[end:]
replace("'scope':'SINGLE_COPY_REMOVAL_REAL_UVC_60S_ALWAYS_RESTORED'",
    "'scope':'THREAD_SWITCH_DUAL_MODEL_120S_ALWAYS_RESTORED'")
replace("'candidate_ui_sha256':'d74e30250e94584217c90eba9efaed41413e72d64505eeecd20d7cce66e7de45'",
    "'candidate_ui_sha256':SOURCE_HASHES['board/vision/ui_camera_service.py'],'source_hashes':SOURCE_HASHES")
replace("'metrics_or_shadow_enabled':False,'requested_observation_s':60",
    "'metrics_enabled':True,'shadow_enabled':False,'runqueue_time_collected':False,'requested_observation_s':120")
replace("timer='aura-capture-copy-live-rollback-'","timer='aura-thread-switch-live-rollback-'")
replace("'--on-active=240s'","'--on-active=360s'")
replace('for index in range(13):','for index in range(25):')
replace('if index<12:','if index<24:')
replace('assert elapsed>=60','assert elapsed>=120')
replace("state=camera();report['latest_camera_seen']=state;healthy(state)\n            assert state['pid']==first['pid'] and state.get('shadow') is None",
    "state=camera();report['latest_camera_seen']=state;save();healthy(state)\n            assert state['pid']==first['pid'] and state.get('shadow') is None\n            observer=state['pipeline_metrics']['optional_diagnostics']['thread_sched_observer']\n            assert observer['enabled'] and observer['mode']=='CALLING_THREAD_CONTEXT_SWITCHES_ONLY'\n            assert not observer['disabled_after_slow_read'],'Observer stopped after slow read'")
replace("report['passed']=True;report['observation_status']='LIVE_CAMERA_SHORT_WINDOW_PASSED_NOT_LONG_STABILITY_OR_GAIN_COMPARISON'",
    "report['passed']=True;report['observation_status']='OBSERVER_120S_RUNTIME_ONLY_NOT_ROOT_CAUSE_OR_GAIN_PROOF'")
replace("report['observation_status']='FAILED'",
    "report['observation_status']='FAILED'\n        try:report['fault_camera_snapshot']=camera()\n        except Exception as fault_error:report['fault_snapshot_error']=type(fault_error).__name__\n        save()")
source=source.replace('capture-copy-launches','thread-switch-launches').replace('AURA_RUN_CAPTURE_COPY_LIVE','AURA_RUN_THREAD_SWITCH_LIVE')
source=source.replace("'aura-capture-copy-live-'+key","'aura-thread-switch-live-'+key").replace('RuntimeMaxSec=210','RuntimeMaxSec=300')
source=source.replace('Read capture-copy-live deployment-result','Read thread-switch-live deployment-result')
source='BUNDLE_SHA='+repr(meta['sha256'])+'\nSOURCE_HASHES='+repr({k:v['sha256'] for k,v in meta['manifest']['files'].items()})+'\n'+source
ast.parse(source)
target=Path('/home/ghmd/aura-identity-dpu-check-20261018/board_thread_switch_live_20261022.py')
if target.exists():assert target.read_text()==source
else:target.write_text(source)
(ROOT/'live-helper-manifest.json').write_text(json.dumps({'helper':str(target),
    'sha256':hashlib.sha256(source.encode()).hexdigest(),'bytes':len(source),'expected_seconds':120,
    'independent_rollback_seconds':360,'runtime_max_seconds':300,'runqueue_collected':False},indent=2)+'\n')
print(json.dumps({'path':str(target),'bytes':len(source)}))
