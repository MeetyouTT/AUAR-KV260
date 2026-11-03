"""Reuse frozen inference sources; change only experimental process startup."""
import ast,base64,hashlib,json
from pathlib import Path

ROOT=Path(__file__).resolve().parent
baseline=Path('/home/ghmd/aura-identity-dpu-check-20261018/board_thread_switch_live_20261022.py')
assert hashlib.sha256(baseline.read_bytes()).hexdigest()=='a439f630bfeb7d86fe93133dd7f287cb30a248a011ecf48950ad4692b5e5694d'
wrapper=(ROOT/'gil_camera_launcher.py').read_bytes()
source=baseline.read_text()
source=source.replace("/thread-switch-live'","/gil-switch-live'").replace('/thread-switch-live','/gil-switch-live')
source=source.replace('thread-switch-launches','gil-switch-launches').replace('AURA_RUN_THREAD_SWITCH_LIVE','AURA_RUN_GIL_SWITCH_LIVE')
source=source.replace('aura-thread-switch-live-rollback-','aura-gil-switch-live-rollback-').replace('aura-thread-switch-live-','aura-gil-switch-live-')
source=source.replace('THREAD_SWITCH_DUAL_MODEL_120S_ALWAYS_RESTORED','GIL_1MS_DUAL_MODEL_120S_ALWAYS_RESTORED')
source=source.replace('Read thread-switch-live deployment-result','Read gil-switch-live deployment-result')
def replace(old,new):
    global source
    assert source.count(old)==1,(old[:80],source.count(old))
    source=source.replace(old,new)
replace("    assert updated!=original_unit",r'''
    import base64
    wrapper=folder/'gil_camera_launcher.py';wrapper.write_bytes(base64.b64decode(WRAPPER_B64))
    assert digest(wrapper)==WRAPPER_SHA
    target=str(candidate/'tools/board_camera_motion.py')
    assert digest(target)=='1e0e6f0b8881c2d4d4cf81a2527e79d063e673eeba1d069e33bdde2608303005'
    text=updated.decode();assert text.count(target)==1
    text=text.replace(target,str(wrapper)+' '+target)
    assert text.count('[Service]\n')==1
    text=text.replace('[Service]\n','[Service]\nEnvironment="AURA_EXPERIMENT_GIL_MS=1"\n')
    updated=text.encode()
    assert updated!=original_unit
''')
replace("'runqueue_time_collected':False,'requested_observation_s':120",
    "'runqueue_time_collected':False,'requested_observation_s':120,'experimental_gil_requested_ms':1,\n        'wrapper_sha256':WRAPPER_SHA,'native_sources_unchanged_from_5ms_observer':True")
replace("single_owner(state['pid']);first=state;started=time.monotonic();first_cpu=cpu()",r'''
        single_owner(state['pid'])
        startup=json.loads((folder/('process-setting-'+str(state['pid'])+'.json')).read_text())
        assert startup['pid']==state['pid'] and startup['requested_ms']==1
        assert abs(startup['actual_start_seconds']-.001)<1e-9
        report['experimental_process_setting']=startup
        first=state;started=time.monotonic();first_cpu=cpu()
''')
replace("report['passed']=True;report['observation_status']='OBSERVER_120S_RUNTIME_ONLY_NOT_ROOT_CAUSE_OR_GAIN_PROOF'",r'''
        diagnostics=state['pipeline_metrics']['optional_diagnostics']
        assert not diagnostics['fault_events'] and not diagnostics['diagnostic_errors']
        assert diagnostics['counters']['yunet']['native_completed']>=100
        report['observed_yunet_hz']=(state['dpu_schedule']['optional']['yunet']['calls']-first['dpu_schedule']['optional']['yunet']['calls'])/elapsed
        assert report['observed_yunet_hz']>=2.
        report['passed']=True;report['observation_status']='GIL_1MS_SHORT_WINDOW_ONLY_NOT_ROOT_CAUSE_OR_LONG_STABILITY_PROOF'
''')
prefix='WRAPPER_B64='+repr(base64.b64encode(wrapper).decode())+'\nWRAPPER_SHA='+repr(hashlib.sha256(wrapper).hexdigest())+'\n'
source=prefix+source
ast.parse(source)
assert not any(isinstance(n,ast.Constant) and n.value=='\\n' for n in ast.walk(ast.parse(source)))
target=Path('/home/ghmd/aura-identity-dpu-check-20261018/board_gil_switch_1ms_20261022.py')
if target.exists():assert target.read_text()==source
else:target.write_text(source)
meta={'helper':str(target),'sha256':hashlib.sha256(source.encode()).hexdigest(),
    'wrapper_sha256':hashlib.sha256(wrapper).hexdigest(),'source_bundle_sha256':
    'cbee206f503bab019812b3ba3943a54943e8913568a5fcd0cecab0f7358b258f',
    'trial_switch_seconds':.001,'seconds':120,'independent_rollback_seconds':360,
    'native_runtime_budget_or_affinity_changed':False}
(ROOT/'trial-manifest.json').write_text(json.dumps(meta,indent=2)+'\n')
print(json.dumps(meta))
