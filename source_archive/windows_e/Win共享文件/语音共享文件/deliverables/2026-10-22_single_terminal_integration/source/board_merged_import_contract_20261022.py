BUNDLE_SHA='0dd98eee68320ec7fbf5e60832f88360a88272ffa0ff21423eead8bfccee9d33'
"""Merged-source compatibility only; no camera, DPU runner or identity store."""
import ast,builtins,hashlib,importlib,json,sqlite3,sys,tarfile,threading,time,urllib.request
from pathlib import Path
from types import SimpleNamespace

assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()=='215c4292-ce84-4828-9827-83c32ba66564'
original=Path('/home/root/aura-dpu-vision-20261021/runtime/81fdb11903abb71e-live-134783/aura')
op=urllib.request.build_opener(urllib.request.ProxyHandler({}))
def health():
    with op.open('http://127.0.0.1:8790/health',timeout=3) as f:s=json.load(f)
    return {k:s.get(k) for k in ('pid','detected_frames','camera_error','detector_error')}
before=health()
bundle=Path('/home/root/aura-dpu-vision-20261021/staging')/BUNDLE_SHA[:16]/'bundle.tar.gz'
assert hashlib.sha256(bundle.read_bytes()).hexdigest()==BUNDLE_SHA
root=Path('/home/root/aura-single-terminal-contract-20261022')/BUNDLE_SHA[:16]
root.mkdir(parents=True,exist_ok=True,mode=0o700)
with tarfile.open(bundle) as archive:
    meta=json.load(archive.extractfile('candidate-manifest.json'))
    assert len(meta['files'])==13 and set(archive.getnames())==set(meta['files'])|{'candidate-manifest.json'}
    for name,row in meta['files'].items():
        assert name.startswith('board/') and name.endswith('.py') and '..' not in Path(name).parts
        item=archive.getmember(name);assert item.isfile() and item.size<=65536
        data=archive.extractfile(item).read()
        assert hashlib.sha256(data).hexdigest()==row['sha256'] and len(data)==row['bytes']
        ast.parse(data.decode(),filename=name)
        target=root/name;target.parent.mkdir(parents=True,exist_ok=True)
        assert not target.is_symlink()
        if target.exists():assert target.read_bytes()==data
        else:
            with target.open('xb') as out:out.write(data)
sys.path.insert(0,str(original))
import board.identity,board.vision
board.identity.__path__.insert(0,str(root/'board/identity'))
board.vision.__path__.insert(0,str(root/'board/vision'))
original_import=builtins.__import__;original_connect=sqlite3.connect
def guarded_import(name,*args,**kwargs):
    if name.split('.')[0] in {'xir','vart'}:raise AssertionError('A compatibility check must not import DPU runtime bindings')
    return original_import(name,*args,**kwargs)
def no_database(*args,**kwargs):raise AssertionError('A compatibility check must not connect to a database')
builtins.__import__=guarded_import;sqlite3.connect=no_database
modules=[]
try:
    for name in sorted(meta['files']):
        module=importlib.import_module(name[:-3].replace('/','.'))
        assert Path(module.__file__).resolve()==(root/name).resolve()
        modules.append(name)
    from board.identity.sface_producer import producer_configuration
    from board.identity.sface_shadow import shadow_configuration
    from board.identity.sface_calibration import calibration_configuration
    assert producer_configuration({}) is None and shadow_configuration({}) is None and calibration_configuration({}) is None
    from board.identity.camera_faces import config_for
    config=config_for(original,original.parent/'board_identity.json')
    assert config['feature_backend']['kind']=='windows_sface'
    assert config.get('dpu_sface_producer') is None and config.get('dpu_sface_calibration') is None
    from board.vision.pipeline_metrics import OptionalDiagnostics
    from board.vision.dpu_vision_schedule import DpuVisionSchedule
    diagnostics=OptionalDiagnostics(enabled=True)
    schedule=DpuVisionSchedule(diagnostics=diagnostics)
    schedule.next_primary=time.monotonic()+.1
    with schedule.optional('yunet') as acquired:
        assert acquired
        for phase in ['execute_start','execute_return','wait_start']:diagnostics.native_mark('yunet',phase)
        diagnostics.native_mark('yunet','wait_end',0)
    snap=diagnostics.snapshot()
    assert snap['normal_success_timings']['yunet']['wait_wall_ms']['count']==1
    assert len(snap['fault_events'])==0 and snap['maximum_normal_trace'] is not None
finally:
    builtins.__import__=original_import;sqlite3.connect=original_connect
after=health()
assert after['pid']==before['pid'] and after['detected_frames']>=before['detected_frames']
assert not after['camera_error'] and not after['detector_error']
print(json.dumps({'status':'MERGED_IMPORT_CONFIG_AND_SYNTHETIC_DIAGNOSTIC_CONTRACT_ONLY',
    'source_bundle_sha256':BUNDLE_SHA,'modules_verified':len(modules),'python':sys.version.split()[0],
    'default_auxiliary_features_disabled':True,'original_windows_config_valid':True,
    'synthetic_normal_timing_checks_passed':True,'synthetic_native_completed_marks':1,
    'actual_dpu_jobs_executed':0,'new_camera_or_audio_opened':False,'identity_database_opened':False,
    'production_service_modified':False,'runtime_inference_wiring_board_verified':False,
    'camera_before':before,'camera_after':after}),flush=True)
