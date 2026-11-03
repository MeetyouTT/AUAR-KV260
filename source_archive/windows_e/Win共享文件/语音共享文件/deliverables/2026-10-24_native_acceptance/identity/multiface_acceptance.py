"""Read-only two-person ambiguity gate; no private identity data is exported."""
import hashlib,json,subprocess,sys,time,urllib.request
from pathlib import Path

source=Path(__file__).resolve();token=hashlib.sha256(source.read_bytes()).hexdigest()[:16]
root=Path('/home/root/aura-native-acceptance-20261024')/token
root.mkdir(parents=True,exist_ok=True,mode=0o700)
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()=='a69299ef-17d0-446f-a0df-56c0a08cd2fb'
if sys.argv[1:]!=['--worker']:
    assert not sys.argv[1:] and not (root/'launch.json').exists()
    (root/'launch.json').write_text(json.dumps({'ground_truth':'two_people_explicit_ready',
        'duration_seconds':20,'minimum_multiface_samples':15,'maximum_single_identity_bindings':0,
        'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest()})+'\n')
    p=subprocess.run(['systemd-run','--no-block','--quiet','--unit=aura-multiface-acceptance-'+token,
        '--property=Type=oneshot','--property=RuntimeMaxSec=45','--property=Nice=19',
        '/usr/bin/python3','-B',str(source),'--worker'],capture_output=True,text=True,timeout=8)
    assert p.returncode==0,p.stderr
    print(json.dumps({'started':True,'root':str(root),'seconds':20,'no_mutation':True}))
    raise SystemExit(0)

op=urllib.request.build_opener(urllib.request.ProxyHandler({}))
def get(path):
    with op.open('http://127.0.0.1:8790'+path,timeout=3) as stream:return json.load(stream)
def counters(h):
    s=h['dpu_schedule'];i=h['identity'];face=i['face_targets']
    return dict(pid=h['pid'],detected=h['detected_frames'],primary_overruns=s['primary_period_overruns'],
        optional_overruns={k:s['optional'][k]['overruns'] for k in ['yunet','sface']},
        gaps=face['freshness_metrics']['counters']['observed_gap_intervals'],
        sface_completed=i['feature_inference']['completed'],match_counts=i['match_diagnostics']['counts'])

report={'scope':'20_SECONDS_TWO_PEOPLE_SINGLE_IDENTITY_BINDING_REJECTION',
    'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),
    'ground_truth':'two_people_explicit_ready','no_mutation':True,'samples':[],'passed':False,
    'no_images_vectors_names_or_person_ids_saved':True}
try:
    meta=json.loads(Path('/home/root/aura-native-live-20261024/ops/be72669aa53de735/meta.json').read_text())
    config=json.loads(Path(meta['candidate_config']).read_text());identity=Path(config['identity']['config'])
    raw=identity.read_bytes();assert hashlib.sha256(raw).hexdigest()=='398ece6a4d5d81076c9a4f9f40a43e97cedd469e0b47e3a835e589a2255ca6e3'
    database=Path(json.loads(raw)['database']);report['database_sha256_before']=hashlib.sha256(database.read_bytes()).hexdigest()
    before=counters(get('/health'));assert before['pid']==2174;report['before']=before
    began=time.monotonic();next_at=began
    while time.monotonic()-began<20:
        time.sleep(max(0,next_at-time.monotonic()));next_at+=1
        h=get('/health');v=get('/v1/ui/status')['modules']['identity']
        assert h['pid']==before['pid'] and not h['dpu_schedule']['owner_fenced']
        assert h['identity']['face_targets']['worker_alive']
        count=v.get('face_count');eligible=type(count) is int and count>=2
        report['samples'].append(dict(elapsed_seconds=time.monotonic()-began,face_count=count,
            eligible_multiface=eligible,public_state=v.get('state'),
            single_face_target_present=bool(v.get('face_target')),
            identity_id_present=bool(v.get('person_id')),
            classified_known=v.get('state')=='KNOWN',
            feature_ready=h['identity']['feature_inference']['ready']))
    after=counters(get('/health'));seconds=time.monotonic()-began
    assert after['pid']==before['pid'];report['after']=after;report['duration_seconds']=seconds
    eligible=[row for row in report['samples'] if row['eligible_multiface']]
    leaked=[row for row in eligible if row['single_face_target_present'] or row['identity_id_present'] or row['classified_known']]
    report['multiface_samples']=len(eligible);report['single_identity_binding_samples']=len(leaked)
    report['yolo_hz']=(after['detected']-before['detected'])/seconds
    report['new_primary_overruns']=after['primary_overruns']-before['primary_overruns']
    report['new_gaps']=after['gaps']-before['gaps']
    report['new_sface_completed']=after['sface_completed']-before['sface_completed']
    report['new_match_counts']={k:after['match_counts'][k]-before['match_counts'][k] for k in before['match_counts']}
    report['database_sha256_after']=hashlib.sha256(database.read_bytes()).hexdigest()
    report['passed']=len(eligible)>=15 and not leaked and not report['new_primary_overruns'] and not report['new_gaps'] \
        and before['optional_overruns']==after['optional_overruns'] and report['yolo_hz']>=9.5 \
        and report['database_sha256_before']==report['database_sha256_after']
except BaseException as exc:report['failure']=type(exc).__name__+': '+str(exc)
finally:
    with (root/'report.json').open('x') as out:json.dump(report,out,indent=2);out.write('\n')
    print(json.dumps({'report_path':str(root/'report.json'),'passed':report['passed'],
        'multiface_samples':report.get('multiface_samples'),'failure':report.get('failure')}))
