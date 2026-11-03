"""Extend the already reviewed two-model observation, no inference source changes."""
import ast,hashlib,json
from pathlib import Path

short=Path('/home/ghmd/aura-identity-dpu-check-20261018/board_yunet_diagnostic_20261022_v2.py')
assert hashlib.sha256(short.read_bytes()).hexdigest()=='161ba8545a3df969c56fc2ae05171c3df4084ee5b58d64a54cc589bb27cbeef1'
source=short.read_text()
changes={
    'YUNET_OPTIONAL_DIAGNOSTIC_120S_ALWAYS_RESTORED':'YUNET_OPTIONAL_DIAGNOSTIC_600S_ALWAYS_RESTORED',
    "'seconds':120,'actual_yunet_wait_successes_minimum':3":"'seconds':600,'actual_yunet_wait_successes_minimum':3",
    "'--on-active=360s'":"'--on-active=900s'",
    'range(25)':'range(121)',
    'index==24':'index==120',
    'index<24':'index<120',
    'assert dt>=120 and completed>=3':'assert dt>=600 and completed>=3',
    "'--property=RuntimeMaxSec=280'":"'--property=RuntimeMaxSec=800'",
}
for old,new in changes.items():
    assert source.count(old)==1,old
    source=source.replace(old,new,1)
ast.parse(source)
out=short.with_name('board_yunet_diagnostic_20261022_600s.py')
if out.exists():assert out.read_text()==source
else:out.write_text(source)
ns={'__name__':'_extended_diagnostic_test'};exec(compile(source,str(out),'exec'),ns)
base={'samples':[{'detected_frames':10,'dpu_schedule':{'optional':{'yunet':{'calls':3}}}}],
    'camera_after':{'detected_frames':6010,'dpu_schedule':{'optional':{'yunet':{'calls':1503}}},
        'pipeline_metrics':{'stages':{'yunet.execute_wait':{'count':1500}}},'shadow':None},
    'observation_elapsed_s':600.,'usb_audio_warning_count':0}
ns['validate_diagnostic'](base)
assert base['passed'] and base['formal_identity_or_long_run_accepted'] is False
assert base['observed_yolo_hz']==10
base['observation_elapsed_s']=599.
try:ns['validate_diagnostic'](base)
except AssertionError:pass
else:raise AssertionError('Extended duration gate failed')
value={'source_sha256':hashlib.sha256(out.read_bytes()).hexdigest(),'source':str(out),
    'unchanged_four_source_bundle_sha256':'684f232ba4be7e3bdc4b8a5092bdfc527f564f615a78f46c65d80956dcd3b921',
    'duration_s':600,'controller_changes':changes,'syntax_passed':True,
    'synthetic_pass_scope_and_duration_gate_checked':True,'formal_or_30min_acceptance':False}
Path('/home/ghmd/aura-cpu-dpu-implementation-20261022/extended-diagnostic-preparation.json').write_text(json.dumps(value,indent=2)+'\n')
print(json.dumps(value))
