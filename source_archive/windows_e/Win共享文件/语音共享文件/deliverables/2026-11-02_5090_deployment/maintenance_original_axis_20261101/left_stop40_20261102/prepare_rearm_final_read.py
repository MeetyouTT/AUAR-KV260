import ast
from pathlib import Path
HERE=Path(__file__).resolve().parent;NEW=HERE/'recovery_stability_20261102_v3'
s=(HERE/'py39_fix/final_readonly.py').read_text(encoding='utf-8')
changes={
    'control-10282601-left40-right45-py39-14e598cf':'control-10282601-left40-right45-stable150-35d5e154',
    '941b8fc4814eabecf3063b74a968b17a2b649c9573e4f2d04698a780a8fe7c74':'1177df3831407bc819c1f1e3b89090f8c6b97661c8e74c2866b281be93b0a9c8',
    "assert params['left_target_center_ratio']==.4 and params['target_center_ratio']==.45 and params['center_tolerance_ratio']==.03":
    "assert params['left_target_center_ratio']==.4 and params['target_center_ratio']==.45 and params['center_tolerance_ratio']==.03\nassert params['rearm_stability_ms']==150 and params['rearm_stability_minimum_distinct_sources']==3 and params['rearm_stability_requires_new_detection'] is True",
    "runtime_fault_count=len(faults) if isinstance(faults,(list,dict)) else None":
    "runtime_fault_count=faults.get('count') if isinstance(faults,dict) else len(faults) if isinstance(faults,list) else None",
    "'segments','visual_center_completions','target_center_ratio','recenter_state','recenter_intent_pending'":
    "'segments','visual_center_completions','target_center_ratio','recenter_state','recenter_intent_pending','rearm_stability_ms','rearm_stability_gate','rearm_stability_waits','rearm_stability_passes','events'",
    "configured_targets=dict(left=.4,right=.45,tolerance=.03)":"configured_targets=dict(left=.4,right=.45,tolerance=.03,rearm_stability_ms=150)",
}
for old,new in changes.items():
    assert s.count(old)==1,(old,s.count(old));s=s.replace(old,new,1)
ast.parse(s);p=NEW/'final_readonly.py';assert not p.exists();p.write_text(s,encoding='utf-8')
print(str(p))
