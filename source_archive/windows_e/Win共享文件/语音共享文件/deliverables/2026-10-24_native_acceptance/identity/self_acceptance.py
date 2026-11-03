"""Read-only self-reported identity check: no images, IDs or vectors exported."""
import hashlib,json,subprocess,sys,time,urllib.request
from pathlib import Path

source=Path(__file__).resolve()
token=hashlib.sha256(source.read_bytes()).hexdigest()[:16]
root=Path('/home/root/aura-native-acceptance-20261024')/token
root.mkdir(parents=True,exist_ok=True,mode=0o700)
BOOT='a69299ef-17d0-446f-a0df-56c0a08cd2fb'
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==BOOT
if sys.argv[1:]!=['--worker']:
    assert not sys.argv[1:] and not (root/'launch.json').exists()
    (root/'launch.json').write_text(json.dumps({'ground_truth':'user_declared_registered_self',
        'duration_seconds':60,'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),
        'acceptance_targets':{'minimum_new_features':20,'minimum_eligible_single_face_samples':45,
            'known_decision_fraction':.90,'expected_identity_presentation_fraction':.90,
            'max_new_overruns_or_gaps':0,'minimum_yolo_hz':9.5}})+'\n')
    command=['systemd-run','--no-block','--quiet','--unit=aura-self-acceptance-'+token,
        '--property=Type=oneshot','--property=RuntimeMaxSec=90','--property=Nice=19',
        '/usr/bin/python3','-B',str(source),'--worker']
    run=subprocess.run(command,capture_output=True,text=True,timeout=8)
    assert run.returncode==0,run.stderr
    print(json.dumps({'started':True,'root':str(root),'ground_truth':'user_declared_registered_self',
        'seconds':60,'no_camera_db_or_model_mutation':True}))
    raise SystemExit(0)

opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
def get(path):
    with opener.open('http://127.0.0.1:8790'+path,timeout=3) as stream:return json.load(stream)
def slim(h):
    schedule=h['dpu_schedule'];identity=h['identity'];face=identity['face_targets']
    return dict(pid=h['pid'],detected=h['detected_frames'],primary_overruns=schedule['primary_period_overruns'],
        optional_overruns={k:schedule['optional'][k]['overruns'] for k in ('yunet','sface')},
        native_completed={k:schedule['optional'][k]['native_completed'] for k in ('yunet','sface')},
        gaps=face['freshness_metrics']['counters']['observed_gap_intervals'],
        sface_completed=identity['feature_inference']['completed'],match_counts=identity['match_diagnostics']['counts'])

report={'scope':'60_SECONDS_REGISTERED_SELF_USER_DECLARED_NOT_GENERAL_ACCURACY',
    'boot':BOOT,'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),
    'no_mutation':True,'ground_truth':'user_declared_registered_self',
    'no_images_vectors_names_or_person_ids_saved':True,'samples':[],'passed':False,
    'sampling_scope':'Health and public view are sequential reads; presentation samples are not independent model decisions'}
try:
    meta=json.loads(Path('/home/root/aura-native-live-20261024/ops/be72669aa53de735/meta.json').read_text())
    config=json.loads(Path(meta['candidate_config']).read_text());identity_path=Path(config['identity']['config'])
    raw=identity_path.read_bytes();assert hashlib.sha256(raw).hexdigest()=='398ece6a4d5d81076c9a4f9f40a43e97cedd469e0b47e3a835e589a2255ca6e3'
    cfg=json.loads(raw);database=Path(cfg['database'])
    report['identity_config_sha256']=hashlib.sha256(raw).hexdigest()
    report['database_sha256_before']=hashlib.sha256(database.read_bytes()).hexdigest()
    report['thresholds']={k:cfg.get(k) for k in ['match_threshold','threshold','ambiguity_margin','result_ttl_ms']}
    health=get('/health');assert health['pid']==2174 and not health['dpu_schedule']['owner_fenced']
    view=get('/v1/ui/status')['modules']['identity'];people=view['people']
    assert len(people)==1,'Self label requires exactly one registered identity; do not guess among multiple people'
    expected=people[0]['person_id'] # In-memory comparison only; never serialized.
    report['registered_people_count']=1
    before=slim(health);report['before']=before
    began=time.monotonic();next_at=began
    while time.monotonic()-began<60:
        time.sleep(max(0,next_at-time.monotonic()));next_at+=1
        health=get('/health');identity=health['identity'];schedule=health['dpu_schedule']
        assert health['pid']==before['pid'] and not schedule['owner_fenced']
        assert identity['ready'] and identity['face_targets']['worker_alive']
        assert {k:schedule['optional'][k]['overruns'] for k in ('yunet','sface')}==before['optional_overruns']
        view=get('/v1/ui/status')['modules']['identity'];now_ms=time.monotonic_ns()//1_000_000
        assert [p['person_id'] for p in view['people']]==[expected],'Identity database membership changed'
        stamp=view.get('source_mono_ms');age=now_ms-stamp if type(stamp) is int else None
        face_count=view.get('face_count');eligible=face_count==1
        report['samples'].append(dict(elapsed_seconds=time.monotonic()-began,
            face_count=face_count,eligible_single_face=eligible,state=view.get('state'),
            expected_identity=(view.get('state')=='KNOWN' and view.get('person_id')==expected),
            wrong_known_identity=(view.get('state')=='KNOWN' and view.get('person_id')!=expected),
            source_age_ms=age,last_decision_state=identity['match_diagnostics']['last_state'],
            last_score=identity['match_diagnostics']['last_score'],
            sface_completed=identity['feature_inference']['completed']))
    after=slim(get('/health'));report['after']=after;seconds=time.monotonic()-began
    report['duration_seconds']=seconds
    delta={k:after['match_counts'][k]-before['match_counts'][k] for k in before['match_counts']}
    assert all(v>=0 for v in delta.values())
    eligible=[row for row in report['samples'] if row['eligible_single_face']]
    known=sum(row['expected_identity'] for row in eligible)
    total=sum(delta.values());features=after['sface_completed']-before['sface_completed']
    report['decision_deltas']=delta;report['new_features']=features
    report['eligible_samples']=len(eligible);report['expected_identity_samples']=known
    report['known_decision_fraction']=delta['KNOWN']/total if total else None
    report['expected_identity_presentation_fraction']=known/len(eligible) if eligible else None
    report['wrong_known_samples']=sum(row['wrong_known_identity'] for row in report['samples'])
    report['stale_known_samples']=sum(row['state']=='KNOWN' and (row['source_age_ms'] is None or not 0<=row['source_age_ms']<cfg['result_ttl_ms']) for row in report['samples'])
    report['yolo_hz']=(after['detected']-before['detected'])/seconds
    report['new_primary_overruns']=after['primary_overruns']-before['primary_overruns']
    report['new_gaps']=after['gaps']-before['gaps']
    report['database_sha256_after']=hashlib.sha256(database.read_bytes()).hexdigest()
    report['data_coverage_sufficient']=features>=20 and len(eligible)>=45
    report['passed']=bool(report['data_coverage_sufficient'] and total and delta['KNOWN']/total>=.90
        and known/len(eligible)>=.90 and not report['wrong_known_samples'] and not report['stale_known_samples']
        and not report['new_primary_overruns'] and not report['new_gaps'] and report['yolo_hz']>=9.5
        and before['optional_overruns']==after['optional_overruns']
        and report['database_sha256_before']==report['database_sha256_after'])
except BaseException as exc:report['failure']=type(exc).__name__+': '+str(exc)
finally:
    with (root/'report.json').open('x') as stream:json.dump(report,stream,indent=2);stream.write('\n')
    print(json.dumps({'report_path':str(root/'report.json'),'passed':report['passed'],
        'failure':report.get('failure'),'new_features':report.get('new_features')}))
