import ast
import hashlib
import json
from pathlib import Path
HERE=Path(__file__).resolve().parent;NEW=HERE/'recovery_stability_20261102_v3';PREVIOUS=HERE/'py39_fix'
r=json.loads((NEW/'APPLIED.json').read_text(encoding='utf-8'))
assert r['status']=='ORIGINAL_FOLLOW_LEFT40_RIGHT45_STABLE150_SELECTED_STOPPED'
s=(PREVIOUS/'start_original_ui_once.py').read_text(encoding='utf-8')
changes={
    'control-10282601-left40-right45-py39-14e598cf':'control-10282601-left40-right45-stable150-35d5e154',
    'original-follow-left40-right45-v2-py39':'original-follow-left40-right45-v3-stable150',
    'da3ecf2fd05f3146ab56c1c969090c9902d3b7af2d1b5753d5e41307f1e9afed':r['controller_manifest_sha256'],
    '941b8fc4814eabecf3063b74a968b17a2b649c9573e4f2d04698a780a8fe7c74':r['startup_after_sha256'],
    "assert face['arguments']['left-target-center-ratio']=='0.40' and face['arguments']['target-center-ratio']=='0.45'":
    "assert face['arguments']['left-target-center-ratio']=='0.40' and face['arguments']['target-center-ratio']=='0.45' and face['arguments']['rearm-stability-ms']=='150'",
    "'recenter_intent_pending','motion_mode','readback','hardware_width_trace'":
    "'recenter_intent_pending','motion_mode','readback','hardware_width_trace','rearm_stability_ms','rearm_stability_gate','rearm_stability_waits','rearm_stability_passes','events'",
    "assert params['center_tolerance_ratio']==.03 and params['hardware_slew_recenter'] is True":
    "assert params['center_tolerance_ratio']==.03 and params['hardware_slew_recenter'] is True\n        assert params['rearm_stability_ms']==150 and params['rearm_stability_minimum_distinct_sources']==3 and params['rearm_stability_requires_new_detection'] is True",
    'end=time.monotonic()+10':'end=time.monotonic()+15',
    'ORIGINAL_UI_STARTED_NEW_TARGETS_CONFIRMED':'ORIGINAL_UI_STARTED_TARGETS_AND_STABILITY150_CONFIRMED',
}
for old,new in changes.items():
    assert s.count(old)==1,(old,s.count(old));s=s.replace(old,new,1)
ast.parse(s);p=NEW/'start_original_ui_once.py';assert not p.exists();p.write_text(s,encoding='utf-8')
print(json.dumps(dict(script_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),original_ui_command_once='pan_face_follow',observe_s=15)))
