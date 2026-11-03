"""Verify v3 scope and rerun only the five independently reproduced regressions."""
import ast
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import threading

HERE=Path(__file__).resolve().parent
CAMERA=HERE.parent/'camera'
original=(CAMERA/'baseline/9d714b9bd00e__ui_camera_service.py').read_bytes()
candidate=(CAMERA/'candidate_v3/ui_camera_service.py').read_bytes()
assert hashlib.sha256(original).hexdigest()=='9d714b9bd00ea1da12088fa1e22100d7bdb689d0cac10332c3933b31e4f4d2df'
assert hashlib.sha256(candidate).hexdigest()=='7d4773b8ff527773eefc90aa2443dd4bfae801f07c6fcde672af65dd22ff8f66'
before=ast.parse(original);after=ast.parse(candidate)
def top(tree):return {n.name:n for n in tree.body if isinstance(n,(ast.ClassDef,ast.FunctionDef))}
old,new=top(before),top(after)
assert set(new)-set(old)=={'_PreviewJpeg'}
assert all(ast.dump(old[key])==ast.dump(new[key]) for key in old if key not in ('CameraState','run'))
checks=['all original top-level definitions except CameraState/run unchanged; only _PreviewJpeg added']
def methods(klass):return {n.name:n for n in klass.body if isinstance(n,ast.FunctionDef)}
om,nm=methods(old['CameraState']),methods(new['CameraState'])
assert set(nm)-set(om)=={'preview_failed'}
assert {key for key in om if ast.dump(om[key])!=ast.dump(nm[key])}=={'__init__','publish_preview','preview','health'}
checks.append('capture, observations, snapshot, identity/command and original HTTP handlers unchanged')
old_run,new_run=old['run'],copy.deepcopy(new['run'])
old_preview=next(n for n in ast.walk(old_run) if isinstance(n,ast.FunctionDef) and n.name=='preview')
new_preview=next(n for n in ast.walk(new_run) if isinstance(n,ast.FunctionDef) and n.name=='preview')
old_try=next(n for n in ast.walk(old_preview) if isinstance(n,ast.Try))
new_try=next(n for n in ast.walk(new_preview) if isinstance(n,ast.Try))
def encode_assignment(node):
    return isinstance(node,ast.Assign) and isinstance(node.value,ast.Call) and isinstance(node.value.func,ast.Attribute) and node.value.func.attr=='imencode'
index=next(i for i,n in enumerate(old_try.body) if encode_assignment(n))
new_index=next(i for i,n in enumerate(new_try.body) if isinstance(n,ast.Expr) and isinstance(n.value,ast.Call) and isinstance(n.value.func,ast.Attribute) and n.value.func.attr=='publish_preview')
new_try.body[new_index:new_index+1]=copy.deepcopy(old_try.body[index:index+3])
new_try.handlers[0].body=copy.deepcopy(old_try.handlers[0].body)
assert ast.dump(old_run)==ast.dump(new_run)
checks.append('normalizing only lazy publication and producer-error helper makes entire run AST identical')

helper_path=CAMERA/'test_lazy_jpeg_v3.py'
assert hashlib.sha256(helper_path.read_bytes()).hexdigest()=='16aa1c8c5d17f3e42cf9d395b65b1da071b99454959eec8dc081df77f0e525cc'
spec=importlib.util.spec_from_file_location('camera_v3_independent_helpers',helper_path)
helpers=importlib.util.module_from_spec(spec);spec.loader.exec_module(helpers)
namespace={'helpers':helpers,'threading':threading}
for path,names in ((HERE/'review_camera_lazy_jpeg.py',{'stale_request_race'}),
                   (HERE/'check_camera_producer_edges.py',{'producer_failed','error_after_request_started','error_before_cached_request','duplicate_frame_waiters'})):
    functions=[n for n in ast.parse(path.read_text(encoding='utf-8')).body if isinstance(n,ast.FunctionDef) and n.name in names]
    assert len(functions)==len(names)
    exec(compile(ast.Module(body=functions,type_ignores=[]),'<previous-independent-regressions>','exec'),namespace)
races=[namespace['stale_request_race']('ok','raise'),namespace['stale_request_race']('raise','ok')]
assert not any(r['stale_request_changed_latest_error'] for r in races)
producer_after=namespace['error_after_request_started']()
producer_before=namespace['error_before_cached_request']()
assert producer_after['newer_producer_error_preserved'] and producer_before['newer_producer_error_preserved']
duplicates=namespace['duplicate_frame_waiters']()
assert duplicates['retired_waiter_owned_images']==0 and duplicates['unneeded_old_encodes']==0
checks.append('all five independent v2/latest-only blocker reproductions now pass against actual v3')
result={'status':'PASS_STATIC_AND_TARGETED_REGRESSIONS_REAL_CV2_AND_DEPLOYMENT_PENDING',
    'baseline_sha256':hashlib.sha256(original).hexdigest(),
    'candidate_sha256':hashlib.sha256(candidate).hexdigest(),
    'scope_checks':checks,'retained_frame_races':races,
    'producer_error_after_request_start':producer_after,'producer_error_before_cached_request':producer_before,
    'same_fid_waiters':duplicates,
    'unmodified_agent_suite_reused':{'tests':27,'passed':True,'not_rerun':True},
    'actual_loop_unique_fid_confirmed':True,
    'remaining':['root CPU-only real OpenCV synthetic byte-equivalence probe',
        'fresh current-boot source closure and normal exact checkpoint restore/readback binding',
        'same-condition current-boot camera/GTK CPU comparison and actual joint dialogue/follow acceptance'],
    'production_candidate_modified':False,'board_or_external_network_or_models_used':False,
    'synthetic_loopback_http_fixture_executed_in_this_review':False,
    'runtime_savings_claimed':False}
(HERE/'CAMERA_V3_INDEPENDENT_REVIEW.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
print(json.dumps(result))
