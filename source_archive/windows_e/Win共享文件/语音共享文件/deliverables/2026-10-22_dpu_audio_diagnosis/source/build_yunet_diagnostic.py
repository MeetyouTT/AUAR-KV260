"""Build a short, always-reverted two-model diagnostic after agent freezes hashes."""
import ast,gzip,hashlib,io,json,runpy,tarfile
from pathlib import Path

ROOT=Path(__file__).resolve().parent
AGENT=Path('/home/ghmd/aura-dpu-audio-diagnosis-20261022')
LIBRARY=Path('/home/ghmd/aura-sface-shadow-candidate-20261021/deploy-preparation/board_shadow_pilot.py')


def sub(source,old,new):
    assert source.count(old)==1,repr(old[:100])
    return source.replace(old,new,1)


def build():
    # This manifest is created by the agent only after regression and freezing.
    freeze=json.loads((AGENT/'patch-manifest.json').read_text())
    assert freeze.get('software_tests_passed',0)>0,'Require frozen passing software checks'
    assert hashlib.sha256(LIBRARY.read_bytes()).hexdigest()=='4bbc86bff5ebd75842940da5b788a43467d54e3905cc95f666f5ae74b958bdb3'
    library=LIBRARY.read_text().split('\ndef main():',1)[0]
    ns={};exec(compile(library,'pinned-library','exec'),ns)
    names=['board/vision/'+name for name in ['pipeline_metrics.py','dpu_vision_runtime.py','dpu_vision_schedule.py','ui_camera_service.py']]
    data={name:(AGENT/'candidate/aura'/name).read_bytes() for name in names}
    files={name:{'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw)} for name,raw in data.items()}
    assert {row['path']:row['sha256'] for row in freeze['source_files']}=={name:row['sha256'] for name,row in files.items()}
    # Agent manifest schema may contain additional review evidence; the complete
    # final manifest itself is pinned in the generated deployment provenance.
    provenance={'agent_manifest_sha256':hashlib.sha256((AGENT/'patch-manifest.json').read_bytes()).hexdigest(),
        'files':files,'baseline':ns['BASELINE'],'scope':'120-second YuNet-only optional diagnostics; original SFace Windows identity unchanged'}
    manifest=(json.dumps(provenance,sort_keys=True,indent=2)+'\n').encode()
    buffer=io.BytesIO()
    with tarfile.open(fileobj=buffer,mode='w') as archive:
        for name,raw in sorted({**data,'patch-manifest.json':manifest}.items()):
            item=tarfile.TarInfo(name);item.size=len(raw);item.mtime=0;item.mode=0o600
            archive.addfile(item,io.BytesIO(raw))
    bundle=gzip.compress(buffer.getvalue(),mtime=0)
    patch_sha=hashlib.sha256(bundle).hexdigest()
    bundle_path=Path('/home/ghmd/aura-dpu-vision-20261021/work/yunet-diagnostic-20261022.tar.gz')
    if bundle_path.exists():assert bundle_path.read_bytes()==bundle
    else:bundle_path.write_bytes(bundle)
    begin=library.index('OVERLAY = {');end=library.index('\n\n\ndef digest',begin)
    library=library[:begin]+'OVERLAY = '+repr({name:v['sha256'] for name,v in files.items()})+library[end:]
    library=sub(library,"'observation_age_ms','camera_error','detector_error','dpu_schedule')", "'observation_age_ms','camera_error','detector_error','dpu_schedule','pipeline_metrics')")
    body=(ROOT/'board_shadow_long.py').read_text()
    body=sub(body,"staging/d6f06aa970649c9e/bundle.tar.gz",'staging/'+patch_sha[:16]+'/bundle.tar.gz')
    body=sub(body,"patch_sha='d6f06aa970649c9e076ccc916ca0c5c3257dcf79639082dd026fa7e90fed95bc'","patch_sha="+repr(patch_sha))
    body=sub(body,"before=camera();healthy(before);single_owner", "before=camera();baseline_health(before);single_owner")
    body=sub(body,"baseline_after=camera();healthy(baseline_after)","baseline_after=camera();baseline_health(baseline_after)")
    body=body.replace("/shadow-long')", "/yunet-diagnostics')")
    start=body.index("    identity['dpu_sface_shadow']={")
    end=body.index("    new_identity=",start)
    body=body[:start]+"    assert identity==saved and 'dpu_sface_shadow' not in identity\n"+body[end:]
    body=sub(body,"    new=old.replace(str(BASE/'aura'),str(candidate)).replace(str(config_path),str(new_config)).encode()",
        "    assert old.count('[Service]\\n')==1 and 'AURA_DPU_DIAGNOSTICS' not in old\n"
        "    new=old.replace(str(BASE/'aura'),str(candidate)).replace(str(config_path),str(new_config))\n"
        "    new=new.replace('[Service]\\n','[Service]\\nEnvironment=AURA_PIPELINE_METRICS=1 AURA_DPU_DIAGNOSTICS=1\\n').encode()")
    body=body.replace('REAL_FACE_THREE_MODEL_SHADOW_1800S_ALWAYS_RESTORED','YUNET_OPTIONAL_DIAGNOSTIC_120S_ALWAYS_RESTORED')
    body=sub(body,"'seconds':1800,'actual_and_accepted_sface_minimum':100", "'seconds':120,'actual_yunet_wait_successes_minimum':3")
    body=sub(body,"'--on-active=2220s'","'--on-active=360s'")
    body=body.replace('healthy(state,True)','healthy(state)')
    body=body.replace('state=camera();healthy(state)','state=camera();report[\'latest_camera_seen\']=state;healthy(state)')
    body=body.replace('range(361)','range(25)').replace('index==360','index==24').replace('index<360','index<24')
    body=sub(body,"state['shadow']['execution']['completed']","state.get('pipeline_metrics',{}).get('stages',{}).get('yunet.execute_wait',{}).get('count',0)")
    body=sub(body,'        validate_observation(report)','        validate_diagnostic(report)')
    body=sub(body,"'last_shadow_completed'","'last_yunet_completed'")
    body=sub(body,'5-second health snapshots and /proc CPU deltas; no new per-stage instrumentation; no XRT collection owned by this script',
        '5-second health snapshots, enabled bounded stage/optional diagnostics and /proc CPU deltas; no XRT collection owned by this script')
    body=sub(body,"'yolo_min_fraction_of_baseline':.95,'sampled_single_face_sface_min_hz':.5,'sampled_single_face_yunet_min_hz':1.5",
        "'formal_identity_accepted':False,'long_run_accepted':False")
    extra='''
def baseline_health(state):
    assert not state['camera_error'] and not state['detector_error']
    assert state['observation_age_ms'] is not None and state['observation_age_ms']<750
    assert state['identity_backend']=='WINDOWS_CPU_SFACE_ORT' and state.get('shadow') is None
    face=state['face_targets']
    assert face['ready'] and not face['error'] and face['backend'] in ('DPU_YUNET_INT8','CPU_YUNET_FALLBACK_AFTER_DPU_OVERRUN')
    usb=Path('/sys/bus/usb/devices/1-1.2')
    assert (usb/'idVendor').read_text().strip()=='17ef' and (usb/'idProduct').read_text().strip()=='a03b'
    assert (usb/'devnum').read_text().strip()=='4','Audio address changed; refuse fixed-boot endpoint observation'

def validate_diagnostic(report):
    first=report['samples'][0];last=report['camera_after'];dt=report['observation_elapsed_s']
    completed=last['pipeline_metrics']['stages']['yunet.execute_wait']['count']
    assert dt>=120 and completed>=3
    assert last.get('shadow') is None and report['usb_audio_warning_count']==0
    assert (last['detected_frames']-first['detected_frames'])/dt>=9.,'Primary throughput below diagnostic gate'
    report.update(passed=True,observation_status='SHORT_DIAGNOSTIC_NO_FAILURE_REPRODUCED',
        diagnostic_completed_waits=completed,formal_identity_or_long_run_accepted=False,
        observed_yolo_hz=(last['detected_frames']-first['detected_frames'])/dt,
        observed_yunet_hz=(last['dpu_schedule']['optional']['yunet']['calls']-first['dpu_schedule']['optional']['yunet']['calls'])/dt)
'''
    launcher='''
if __name__=='__main__':
    import sys
    source=Path(sys._getframe().f_code.co_filename).resolve();key=digest(source)[:16]
    launch=Path('/home/root/aura-dpu-vision-20261021/yunet-diagnostic-launches')/key
    launch.mkdir(parents=True,exist_ok=True)
    if os.environ.get('AURA_RUN_YUNET_DIAGNOSTIC')=='1':
        try:
            main();result={'finished':True,'scope':'Read yunet-diagnostics deployment-result.json for actual diagnostic/restoration'}
        except Exception as exc:result={'finished':True,'error':type(exc).__name__+': '+str(exc)[:500]}
        (launch/'launch-result.json').write_text(json.dumps(result,indent=2)+'\\n')
    else:
        assert not (launch/'launch-result.json').exists()
        unit='aura-yunet-diagnostic-'+key
        command(['systemd-run','--unit='+unit,'--property=RuntimeMaxSec=280',
            '--setenv=AURA_RUN_YUNET_DIAGNOSTIC=1','/usr/bin/python3','-B',str(source)])
        print(json.dumps({'started':True,'unit':unit,'launch_result':str(launch/'launch-result.json')}),flush=True)
'''
    source=library+'\n'+body+'\n'+extra+'\n'+launcher;ast.parse(source)
    out=Path('/home/ghmd/aura-identity-dpu-check-20261018/board_yunet_diagnostic_20261022_v2.py')
    if out.exists():assert out.read_text()==source
    else:out.write_text(source)
    provenance.update(bundle_sha256=patch_sha,helper_sha256=hashlib.sha256(out.read_bytes()).hexdigest(),
        bundle_path=str(bundle_path),helper_path=str(out))
    (ROOT/'diagnostic-deployment-provenance.json').write_text(json.dumps(provenance,indent=2)+'\n')
    print(json.dumps({'bundle_bytes':len(bundle),'bundle_sha256':patch_sha,'helper_sha256':provenance['helper_sha256']}))


if __name__=='__main__':build()
