"""Independent local exact-method review; never executes author report writers."""
import ast
import copy
import hashlib
import json
from pathlib import Path
import sys
from types import ModuleType,SimpleNamespace

HERE=Path(__file__).resolve().parent
AUTHOR=HERE.parent
ASSESS=AUTHOR.parent/'assessment_cases.py'
EXPECTED='aac26f39b8cbec1496df93a3de24b0bc2a14289552d2728c585f3625ef779eae'
SOURCE=AUTHOR/'candidate/board/runtime/board_business.py'
assert hashlib.sha256(SOURCE.read_bytes()).hexdigest()==EXPECTED
author_receipt_before=(AUTHOR/'VALIDATION.json').read_bytes()
author_payload_before=SOURCE.read_bytes()

# Only public class/fixture declarations and constants. Stop before all cases
# and the original assessment's report writer; no real endpoint or anchor.
tree=ast.parse(ASSESS.read_text(encoding='utf-8'))
prefix=[]
for node in tree.body:
    if isinstance(node,ast.Assign) and any(isinstance(n,ast.Name) and n.id=='results' for n in node.targets):break
    prefix.append(node)
fixture=ModuleType('independent_clock_fixture');fixture.__file__=str(ASSESS)
sys.modules[fixture.__name__]=fixture
exec(compile(ast.Module(body=prefix,type_ignores=[]),'<public-fixture-prefix-only>','exec'),fixture.__dict__)

source_tree=ast.parse(SOURCE.read_text(encoding='utf-8'))
runtime_cls=copy.deepcopy(next(n for n in source_tree.body if isinstance(n,ast.ClassDef) and n.name=='BoardBusinessRuntime'))
runtime_cls.body=[n for n in runtime_cls.body if isinstance(n,ast.FunctionDef) and n.name=='initialize_clock']
scope={'copy':copy,'StableTimelineClock':fixture.clock_module.StableTimelineClock,
       'InferenceHttpClient':fixture.namespace['InferenceHttpClient'],'ClockUnavailable':fixture.ClockUnavailable}
exec(compile(ast.Module(body=[runtime_cls],type_ignores=[]),'<exact-reviewed-initialize-clock>','exec'),scope)
Runtime=scope['BoardBusinessRuntime']

def runtime(f,after_error=None):
    r=Runtime();r.timeline=f.timeline;r.client=f.client;r.clock=f.mono;r.boot_id='synthetic-boot'
    r.started=False;r.closed=False;r.config=SimpleNamespace(model_host='192.168.50.1',model_port=8797)
    r._clock_refresh_next=-1;r._clock_refresh_failures=7;r.clock_refresh_error='before'
    original=f.client.sample_health_date
    def observed(timeline,*,deadline,cancelled):
        f.deadlines.append(deadline)
        try:return original(timeline,deadline=deadline,cancelled=cancelled)
        except BaseException:
            if after_error:after_error(f,r)
            raise
    f.client.sample_health_date=observed
    return r

def run(r,f):
    start=f.mono()
    try:result=r.initialize_clock(cancelled=lambda:f.cancelled);outcome='ACCEPTED'
    except BaseException as error:result=error;outcome=type(error).__name__
    assert len(f.calls)<=2
    assert all(d==start+3. for d in f.deadlines)
    if outcome!='ACCEPTED':assert (r._clock_refresh_next,r._clock_refresh_failures,r.clock_refresh_error)==(-1,7,'before')
    return outcome,result

results={}
FAST,SLOW=fixture.FAST,fixture.SLOW

f=fixture.Fixture([SLOW,FAST]);r=runtime(f);state,_=run(r,f)
assert state=='ACCEPTED' and len(f.calls)==2 and f.samples[0] is not f.samples[1]
assert not f.client.validate_sample(f.samples[0]) and f.timeline.policy['max_rtt']==1.
results['independent_slow_fresh_success_and_retired_first_proof']=True

f=fixture.Fixture([FAST]);f.cancelled=True;r=runtime(f);state,_=run(r,f)
assert state=='InterruptedError' and len(f.calls)==0 and f.timeline.anchor is None
results['cancel_before_first_request_no_connection']=True

for label,second in [('second_wrong_role',dict(role='wrong_role')),('second_wrong_peer',dict(peer=('192.168.50.3',8797))),
                     ('second_bad_date',dict(date='not-a-date')),('second_slow',SLOW)]:
    f=fixture.Fixture([SLOW,second,FAST]);r=runtime(f);state,_=run(r,f)
    assert state!='ACCEPTED' and len(f.calls)==2 and f.timeline.anchor is None
    results[label+'_no_third']=True

f=fixture.Fixture([dict(SLOW,role='wrong_role'),FAST]);r=runtime(f);state,_=run(r,f)
assert state=='ModelRequestError' and len(f.calls)==1 and f.samples==[]
results['slow_wrong_role_never_becomes_retryable_RTT']=True

f=fixture.Fixture([SLOW,FAST]);r=runtime(f);factory=f.client.connection_factory
def cancel_in_second_body(*args,**kwargs):
    c=factory(*args,**kwargs)
    if len(f.calls)==2:
        original=c.getresponse
        def response():
            value=original();read=value.read
            def body(limit):
                value=read(limit);f.cancelled=True;return value
            value.read=body;return value
        c.getresponse=response
    return c
f.client.connection_factory=cancel_in_second_body
state,_=run(r,f)
assert state=='InterruptedError' and len(f.calls)==2 and f.timeline.anchor is None and len(f.samples)==1
results['cancel_during_second_body_prevents_observe_and_anchor']=True

f=fixture.Fixture([SLOW,FAST]);f.timeline.status='rejected';f.timeline.last_error='invalid_http_date'
r=runtime(f);state,_=run(r,f)
assert state=='ClockUnavailable' and len(f.calls)==1
results['prior_non_RTT_rejection_not_hidden_by_retry']=True

f=fixture.Fixture([SLOW,FAST]);old=f.timeline.source_validator
r=runtime(f,after_error=lambda f,r:setattr(f.timeline,'source_validator',f.client.validate_sample))
state,_=run(r,f)
assert state=='ACCEPTED' and len(f.calls)==2 and old==f.client.validate_sample and old is not f.client.validate_sample
results['new_bound_method_object_same_client_and_function_is_valid']=True

f=fixture.Fixture([SLOW,FAST]);other=fixture.Fixture([])
r=runtime(f,after_error=lambda f,r:setattr(f.timeline,'source_validator',other.client.validate_sample))
state,_=run(r,f)
assert state=='ClockUnavailable' and len(f.calls)==1
results['different_client_bound_verifier_is_rejected']=True

f=fixture.Fixture([SLOW,FAST]);r=runtime(f);r.started=True;state,_=run(r,f)
assert state=='ClockUnavailable' and len(f.calls)==1
results['already_started_runtime_cannot_retry']=True

f=fixture.Fixture([FAST,SLOW,FAST]);f.anchored_ram_setup();before=copy.deepcopy(f.timeline.anchor)
r=runtime(f);state,_=run(r,f)
assert state=='ACCEPTED' and len(f.calls)==2 and f.timeline.file_revision==0
assert all(f.timeline.anchor[k]==before[k] for k in ('anchor_monotonic','utc_estimate_at_anchor','base_uncertainty_seconds'))
results['RAM_anchor_needs_unchanged_revision_and_unchanged_origin']=True

for fail in (False,True):
    f=fixture.Fixture([FAST,SLOW,FAST]);f.anchored_ram_setup();f.fake_persistence(fail=fail)
    before=copy.deepcopy(f.timeline.anchor);r=runtime(f);state,_=run(r,f)
    assert len(f.calls)==(1 if fail else 2)
    assert (state=='ACCEPTED') is not fail
    assert f.timeline.file_revision==(7 if fail else 9)
    assert all(f.timeline.anchor[k]==before[k] for k in ('anchor_monotonic','utc_estimate_at_anchor','base_uncertainty_seconds'))
    results['persistent_rejection_revision_receipt_'+str(fail)]=True

f=fixture.Fixture([dict(headers=2.95),FAST])
def expire_after_first(f,r):f.mono.value=103.
r=runtime(f,after_error=expire_after_first);state,_=run(r,f)
assert state=='ClockUnavailable' and len(f.calls)==1
results['deadline_consumed_by_first_RTT_does_not_get_new_budget']=True

# Whole-module and intended later composition are structural, not runtime I/O.
baseline=ast.parse((AUTHOR/'baseline/board/runtime/board_business.py').read_text(encoding='utf-8'))
original_cls=next(n for n in baseline.body if isinstance(n,ast.ClassDef) and n.name=='BoardBusinessRuntime')
original_method=next(n for n in original_cls.body if isinstance(n,ast.FunctionDef) and n.name=='initialize_clock')
overlay_cls=next(n for n in source_tree.body if isinstance(n,ast.ClassDef) and n.name=='BoardBusinessRuntime')
overlay_method=next(n for n in overlay_cls.body if isinstance(n,ast.FunctionDef) and n.name=='initialize_clock')
index=overlay_cls.body.index(overlay_method);overlay_cls.body[index]=copy.deepcopy(original_method)
assert ast.dump(source_tree,include_attributes=False)==ast.dump(baseline,include_attributes=False)
results['entire_module_diff_is_only_initialize_clock']=True

split=AUTHOR.parents[2]/'split_commands_20261102/candidate_runtime/board/runtime/board_business.py'
assert hashlib.sha256(split.read_bytes()).hexdigest()=='c01bb04c7bfbce8d78b51aefa5faf0426527be13edf6e26d8d28828c488222b3'
split_tree=ast.parse(split.read_text(encoding='utf-8'));merged=copy.deepcopy(split_tree)
merged_cls=next(n for n in merged.body if isinstance(n,ast.ClassDef) and n.name=='BoardBusinessRuntime')
index=next(i for i,n in enumerate(merged_cls.body) if isinstance(n,ast.FunctionDef) and n.name=='initialize_clock')
previous=merged_cls.body[index];merged_cls.body[index]=copy.deepcopy(overlay_method)
assert any(isinstance(n,ast.ClassDef) and n.name=='LocalIdentityReplies' for n in merged.body)
merged_cls.body[index]=previous
assert ast.dump(merged,include_attributes=False)==ast.dump(split_tree,include_attributes=False)
results['c01bb_AST_method_overlay_preserves_all_standalone_routing']=True

assert SOURCE.read_bytes()==author_payload_before and (AUTHOR/'VALIDATION.json').read_bytes()==author_receipt_before
output={'schema':'aura-clock-overlay-independent-review-1','status':'PASS_NO_CODE_REVIEW_BLOCKERS',
    'candidate_sha256':EXPECTED,'case_count':len(results),'cases':results,
    'author_payload_and_validation_changed':False,'board_network_models_Store_real_anchor_used':False,
    'total_deadline_scope':'Both original client transactions share the original absolute3s deadline; original clock/file operations are not replaced.',
    'real_original_clock_client_executed':True}
(HERE/'REVIEW_VERDICT.json').write_text(json.dumps(output,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'status':output['status'],'cases':len(results),'candidate_sha256':EXPECTED}))
