"""Reuse the reviewed rollback/guard harness for the frozen 13-source merge."""
import ast
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parent
source=Path('/home/ghmd/aura-identity-dpu-check-20261018/board_capture_copy_live_20261022.py').read_text()
meta=json.loads(Path('/home/ghmd/aura-single-terminal-integration-20261022/manifest.json').read_text())
hashes={name:row['sha256'] for name,row in meta['files'].items()}

def replace(old,new):
    global source
    assert source.count(old)==1,(old[:80],source.count(old))
    source=source.replace(old,new)

replace("'detection_hz','observation_age_ms','camera_error','detector_error','dpu_schedule')",
        "'detection_hz','observation_age_ms','camera_error','detector_error','dpu_schedule','pipeline_metrics')")
replace("shadow=(identity.get('feature_inference') or {}).get('shadow'))",
        "shadow=(identity.get('feature_inference') or {}).get('shadow'),\n        producer=(identity.get('feature_inference') or {}).get('producer'))")
replace("folder=Path('/home/root/aura-dpu-vision-20261021/capture-copy-live')/('d74e30250e945842-'+str(os.getpid()))",
        "folder=Path('/home/root/aura-dpu-vision-20261021/merged-live')/('0dd98eee68320ec7-'+str(os.getpid()))")
start=source.index("    path=candidate/'board/vision/ui_camera_service.py'",source.index('def main():'))
end=source.index("    assert updated!=original_unit",start)
source=source[:start]+r'''
    patch=Path('/home/root/aura-dpu-vision-20261021/staging/0dd98eee68320ec7/bundle.tar.gz')
    assert digest(patch)=='0dd98eee68320ec7fbf5e60832f88360a88272ffa0ff21423eead8bfccee9d33'
    expected=MERGED_HASHES
    with tarfile.open(patch,'r:gz') as archive:
        meta=json.load(archive.extractfile('candidate-manifest.json'))
        assert set(meta['files'])==set(expected)
        assert set(archive.getnames())==set(expected)|{'candidate-manifest.json'}
        for rel,sha in expected.items():
            item=archive.getmember(rel);assert item.isfile() and item.size<=65536
            raw=archive.extractfile(item).read()
            assert digest_bytes(raw)==sha==meta['files'][rel]['sha256']
            assert len(raw)==meta['files'][rel]['bytes'];ast.parse(raw.decode(),filename=rel)
            target=candidate/rel;target.parent.mkdir(parents=True,exist_ok=True)
            assert not target.is_symlink();target.write_bytes(raw)
    model=Path('/home/root/aura-dpu-vision-20261021/staging/03580d3216661ba0/kit/sface_public_int8.xmodel')
    manifest=model.with_name('sface-manifest.json')
    manifest_sha='d52e4343910f7d3c775405c161e3fdf16db27396891dc617b0e5defdb878841b'
    assert digest(model)==MODEL_SHA and digest(manifest)==manifest_sha
    saved=json.loads(json.dumps(identity))
    identity['dpu_sface_shadow']={'enabled':True,'model':str(model),'manifest':str(manifest),
        'model_sha256':MODEL_SHA,'manifest_sha256':manifest_sha,'max_source_age_ms':1000,
        'interval_ms':1000,'compare_cosine':False}
    identity['dpu_sface_producer']={'enabled':True,'interval_ms':500}
    assert {k:v for k,v in identity.items() if k not in ('dpu_sface_shadow','dpu_sface_producer')}==saved
    new_identity=folder/'board_identity.json';new_identity.write_text(json.dumps(identity,indent=2)+'\n')
    config=json.loads(original_config.read_text());config['identity']['config']=str(new_identity)
    new_config=folder/'board_camera_ui.json';new_config.write_text(json.dumps(config,indent=2)+'\n')
    path=candidate/'board/vision/ui_camera_service.py'
    updated=original_unit.decode().replace(str(BASE/'aura'),str(candidate)).replace(str(original_config),str(new_config))
    assert updated.count('[Service]\n')==1
    updated=updated.replace('[Service]\n','[Service]\nEnvironment="AURA_PIPELINE_METRICS=1"\nEnvironment="AURA_DPU_DIAGNOSTICS=1"\n').encode()
'''+source[end:]
replace("'scope':'SINGLE_COPY_REMOVAL_REAL_UVC_60S_ALWAYS_RESTORED'",
        "'scope':'MERGED_13_SOURCE_LIVE_60S_SHADOW_ALWAYS_RESTORED'")
replace("'candidate_ui_sha256':'d74e30250e94584217c90eba9efaed41413e72d64505eeecd20d7cce66e7de45'",
        "'candidate_ui_sha256':MERGED_HASHES['board/vision/ui_camera_service.py'],'candidate_source_sha256':MERGED_HASHES")
replace("'metrics_or_shadow_enabled':False", "'metrics_or_shadow_enabled':True,'producer_interval_ms':500,'shadow_interval_ms':1000")
replace("timer='aura-capture-copy-live-rollback-'", "timer='aura-merged-live-rollback-'")
replace("'--on-active=240s'", "'--on-active=300s'")
replace("healthy(state)\n                if runtime_for(state['pid'])==(candidate,original_config)",
        "healthy(state,True)\n                if runtime_for(state['pid'])==(candidate,new_config)")
replace("state=camera();report['latest_camera_seen']=state;healthy(state)\n            assert state['pid']==first['pid'] and state.get('shadow') is None",
        "state=camera();report['latest_camera_seen']=state;save();healthy(state,True)\n            assert state['pid']==first['pid']\n            assert state['producer']['ready'] and not state['producer']['failures']\n            assert state['pipeline_metrics']['enabled'] and state['pipeline_metrics']['optional_diagnostics']['enabled']\n            state['face_count']=face_count()")
replace("report['passed']=True;report['observation_status']='LIVE_CAMERA_SHORT_WINDOW_PASSED_NOT_LONG_STABILITY_OR_GAIN_COMPARISON'",r'''
        diagnostics=state['pipeline_metrics']['optional_diagnostics']
        assert diagnostics['normal_success_timings']['yunet']['wait_wall_ms']['count']>=20
        assert not diagnostics['fault_events'] and not diagnostics['diagnostic_errors']
        assert state['shadow']['same_crop_cosine']['count']==0 and state['shadow']['templates_written']==0
        report['observed_yunet_hz']=(state['dpu_schedule']['optional']['yunet']['calls']-first['dpu_schedule']['optional']['yunet']['calls'])/elapsed
        completed=state['shadow']['execution']['completed']
        report['shadow_completed_total']=completed
        report['shadow_completed_window']=completed-first['shadow']['execution']['completed']
        report['sface_live_verified']=report['shadow_completed_window']>=3
        if report['sface_live_verified']:
            assert diagnostics['normal_success_timings']['sface']['wait_wall_ms']['count']>=3
        report['passed']=True
        report['observation_status']='MERGED_THREE_MODEL_SHORT_WINDOW' if report['sface_live_verified'] else 'MERGED_YUNET_RUNTIME_ONLY_INSUFFICIENT_SFACE_COMPLETIONS'
''')
replace("report['observation_status']='FAILED'",r'''
        report['observation_status']='FAILED'
        try:report['fault_camera_snapshot']=camera()
        except Exception as snapshot_error:report['fault_snapshot_error']=type(snapshot_error).__name__
        save()
''')
replace("'Capture candidate did not become ready'", "'Merged shadow candidate did not become ready'")
replace("'USB warning during copy-only candidate'", "'USB warning during merged candidate'")
replace("'root':str(folder),'passed':report['passed'],'complete':True,\n        'rollback_verified':report['rollback_verified']",
        "'root':str(folder),'passed':report['passed'],'complete':True,\n        'sface_live_verified':report.get('sface_live_verified',False),'rollback_verified':report['rollback_verified']")
# Give each asynchronous run independent owned units and result paths.
source=source.replace('capture-copy-launches','merged-live-launches').replace('AURA_RUN_CAPTURE_COPY_LIVE','AURA_RUN_MERGED_LIVE')
source=source.replace("'aura-capture-copy-live-'+key","'aura-merged-live-'+key").replace('RuntimeMaxSec=210','RuntimeMaxSec=270')
source=source.replace('Read capture-copy-live deployment-result','Read merged-live deployment-result')
source='MERGED_HASHES='+repr(hashes)+'\ndef digest_bytes(raw):return hashlib.sha256(raw).hexdigest()\n'+source
ast.parse(source)
target=Path('/home/ghmd/aura-identity-dpu-check-20261018/board_merged_live_20261022.py')
if target.exists():assert target.read_text()==source
else:target.write_text(source)
(ROOT/'helper-manifest.json').write_text(json.dumps({'source':str(target),
    'sha256':hashlib.sha256(source.encode()).hexdigest(),'bytes':len(source),
    'source_hashes':hashes,'observation_seconds':60,'always_restore':True},indent=2)+'\n')
print(json.dumps({'source':str(target),'bytes':len(source)}))
