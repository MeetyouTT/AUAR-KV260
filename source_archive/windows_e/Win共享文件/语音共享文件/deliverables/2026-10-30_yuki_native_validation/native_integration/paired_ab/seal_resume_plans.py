"""Create new plans, preserving the earlier boot's pilot and 8-case draft."""
from pathlib import Path
import argparse,datetime,hashlib,json

ab=Path(__file__).parent
def read(name):return json.loads((ab/name).read_text(encoding='utf-8-sig'))
def sha(name):return hashlib.sha256((ab/name).read_bytes()).hexdigest()

def main():
    p=argparse.ArgumentParser();p.add_argument('--boot-id',required=True);p.add_argument('--grant',type=Path,required=True);args=p.parse_args()
    baseline=read('fresh-baseline.json');assert baseline['boot_id']==args.boot_id
    proof=read('isolated-server-proof.json');assert proof['status']=='READY_INDEPENDENT_PROCESS'
    assert proof['isolated_port'] not in (8796,proof['production_port'])
    grant=json.loads(args.grant.read_text(encoding='utf-8-sig'))
    assert grant['performance_window']['parallel_stress_during_character_ab'] is False
    state=grant['performance_window']['state']
    assert any(word in state for word in ('RESERVED','GRANTED')) and 'CLOSED' not in state,state
    for name,h in read('harness-delivery-nojpeg-v2.json')['files'].items():assert sha(name)==h,name
    (ab/'resource-window-grant-resume.json').write_text(json.dumps(grant,ensure_ascii=False,indent=2),encoding='utf-8')
    names=['scenario-v1.json','scenario-pilot.json','window-v1.json','public_pcm.wav','public_envelope.json',
           'isolated-server-proof.json','fresh-baseline.json','paired_renderer_harness.py','old_renderer_harness.py',
           'old_harness_support.py','telemetry.py','run_suite.py','resource-window-grant-resume.json']
    common=dict(schema='aura.paired_ab.suite.v1',boot_id=args.boot_id,input_sha256={name:sha(name) for name in names},
                sealed_at_host_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                cooldown_seconds=4,case_timeout_seconds=210,production_switch_authorized=False,
                cost_reduction_predeclared='Require repeatable paired CPU direction exceeding paired variability; whole board and renderer family, PSS/RSS and GPU costs reported separately. Camera or FPS regression counts against candidate. Network delta alone never authorizes replacement.',
                attribution='A-B total pipeline; C-B excludes JPEG but still differs in transport/presenter/snapshot cadence. A-C is time-separated descriptive JPEG-factor estimate, not a precise additive saving.',
                uncertainty='All original runs preserved, including failures. No automatic cutover; GPU utilization UNKNOWN if nodes remain non-updating.')
    for label,cases,scenario in [('control-pilot-resume-v2',['old_nojpeg'],'scenario-pilot.json'),
                                 ('formal-resume-v2',['old','new','new','old','old','new','new','old','old_nojpeg','new','new','old_nojpeg'],'scenario-v1.json')]:
        target=ab/('suite-'+label+'.json');assert not target.exists(),'Keep earlier sealed attempts; use a new revision name'
        target.write_text(json.dumps(dict(common,label=label,cases=cases,scenario=scenario),ensure_ascii=False,indent=2),encoding='utf-8')
        print(json.dumps(dict(status='SEALED_NOT_EXECUTED',plan=str(target),cases=cases,sha256=sha(target.name))))

if __name__=='__main__':main()
