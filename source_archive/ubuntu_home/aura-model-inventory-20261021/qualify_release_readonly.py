import hashlib,importlib.util,json,math,sys
from pathlib import Path
sys.dont_write_bytecode=True
QUALIFIED_SCOPE='COORDINATED_RECOVERY50_GAP3_1MS_DUAL_MODEL_1800S_ALWAYS_RESTORED'
def finite(value):return type(value) in (int,float) and math.isfinite(value)

def qualify(report,expected_hashes):
    assert report.get('scope')==QUALIFIED_SCOPE
    for key in ('complete','passed','rollback_verified','protected_audio_source_verified','gap_record_retention_passed'):
        assert report.get(key) is True,key
    assert report.get('rollback_timer_left_armed') is False
    assert report.get('error') is None and report.get('rollback_error') is None
    assert report.get('retry_hashes')==expected_hashes
    for key,minimum in (('observed_seconds',1800),('observed_yolo_hz',9),('observed_yunet_hz',2)):
        assert finite(report.get(key)) and report[key]>=minimum,key
    assert type(report.get('native_completed_delta')) is int and report['native_completed_delta']>=3600
    assert type(report.get('usb_warning_count')) is int and report['usb_warning_count']==0
    samples=report['samples'];assert len(samples)==361 and report.get('sample_count')==361
    assert all(type(s['face_targets']['source_age_ms']) is int and 0<=s['face_targets']['source_age_ms']<1000 for s in samples)
    first,last=samples[0]['dpu_schedule'],samples[-1]['dpu_schedule']
    assert first['primary_period_overruns']==last['primary_period_overruns'],'New primary deadline overrun'
    job=last['optional']['yunet'];assert job['overruns']==0 and job['disabled'] is False and job['maximum_ms']<=30
    fresh=report['freshness_final'];assert fresh['schema_version']=='aura-face-freshness-light-3'
    assert fresh['observer_failures']==0 and fresh['gap_records_dropped']==0
    assert all(fresh['counters'][k]==0 for k in ('process_errors','callback_errors','invalid_source_ages',
        'source_clock_pairs_rejected','counter_saturation','observed_gap_intervals','post_commit_at_or_over_ttl'))
    assert report['original_unit_sha256']=='84116d8faf6f4d3972f5f2eac35f8c98cf8ecbe51752a8f78d803aa8a7cdd75c'
    return True
p=Path('/home/root/aura-post-power-20261022/helpers/fda2e51c83dd27b4/source.py')
assert hashlib.sha256(p.read_bytes()).hexdigest()=='fda2e51c83dd27b4e64bc2c9f4129f69fba35b26a95069c20e049ffc3e71de51'
spec=importlib.util.spec_from_file_location('_qualification_parent',p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
rows=sorted(Path('/home/root/aura-dpu-vision-20261021/postpower-retry-live').glob('coordinated50-*/deployment-result.json'),key=lambda p:p.stat().st_mtime)
rows=[p for p in rows if json.loads(p.read_text()).get('scope')==QUALIFIED_SCOPE]
p=rows[-1];d=json.loads(p.read_text());qualify(d,m.RETRY_HASHES)
print(json.dumps({'qualified':True,'report':str(p),'report_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'observed_seconds':d['observed_seconds'],'native_completed_delta':d['native_completed_delta'],'rollback_verified':d['rollback_verified']}))
