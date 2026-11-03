"""Exact candidate initialize_clock + original client/clock; synthetic RAM only."""
import ast
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import threading
import uuid
from types import SimpleNamespace

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('pure_original_fixture',HERE.parent/'assessment_cases.py')
fixture=importlib.util.module_from_spec(spec);sys.modules[spec.name]=fixture;spec.loader.exec_module(fixture)
ClockUnavailable=fixture.ClockUnavailable
SOURCE=HERE/'candidate/board/runtime/board_business.py'
EXPECTED='aac26f39b8cbec1496df93a3de24b0bc2a14289552d2728c585f3625ef779eae'
assert hashlib.sha256(SOURCE.read_bytes()).hexdigest()==EXPECTED
tree=ast.parse(SOURCE.read_text(encoding='utf-8'))
klass=copy.deepcopy(next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='BoardBusinessRuntime'))
klass.body=[n for n in klass.body if isinstance(n,ast.FunctionDef) and n.name=='initialize_clock']
ns={'copy':copy,'StableTimelineClock':fixture.clock_module.StableTimelineClock,
    'InferenceHttpClient':fixture.namespace['InferenceHttpClient'],'ClockUnavailable':ClockUnavailable}
exec(compile(ast.Module(body=[klass],type_ignores=[]),'<exact-overlay-method>','exec'),ns)
Runtime=ns['BoardBusinessRuntime']

def bind(f,after_error=None,replace_error=None):
    r=Runtime();r.clock=f.mono;r.client=f.client;r.timeline=f.timeline;r.boot_id='synthetic-boot'
    r.config=SimpleNamespace(model_host='192.168.50.1',model_port=8797)
    r.started=r.closed=False
    r._clock_refresh_next=-1.;r._clock_refresh_failures=99;r.clock_refresh_error='unchanged-before-success'
    native=f.client.sample_health_date
    def observed(timeline,*,deadline,cancelled):
        f.deadlines.append(deadline)
        try:return native(timeline,deadline=deadline,cancelled=cancelled)
        except Exception as exc:
            if after_error:after_error(f,r)
            if replace_error:raise replace_error from exc
            raise
    f.client.sample_health_date=observed
    return r

def run(r,f):
    start=f.mono()
    try:
        result=r.initialize_clock(timeout=3.,cancelled=lambda:f.cancelled)
        outcome='ACCEPTED'
    except Exception as exc:
        result=exc
        outcome='REJECTED'
    assert len(f.calls)<=2
    assert not f.deadlines or len(set(f.deadlines))==1
    if f.deadlines:assert f.deadlines[0]==start+3.
    return outcome,result

results={}
FAST,SLOW=fixture.FAST,fixture.SLOW
f=fixture.Fixture([SLOW,FAST]);r=bind(f);policy=copy.deepcopy(f.timeline.policy)
outcome,_=run(r,f)
assert outcome=='ACCEPTED' and len(f.calls)==2 and f.timeline.policy==policy and policy['max_rtt']==1.
assert f.samples[0] is not f.samples[1] and f.client.validate_sample(f.samples[0]) is False
assert r._clock_refresh_failures==0 and r.clock_refresh_error=='' and r._clock_refresh_next==f.mono()+600.
results['slow_then_fresh_fast']=True

f=fixture.Fixture([FAST]);r=bind(f);outcome,_=run(r,f)
assert outcome=='ACCEPTED' and len(f.calls)==1
results['first_success_one_request']=True

f=fixture.Fixture([SLOW,SLOW,FAST]);r=bind(f);outcome,exc=run(r,f)
assert outcome=='REJECTED' and exc.args==('sample_rtt_exceeded',) and len(f.calls)==2 and f.timeline.anchor is None
assert (r._clock_refresh_next,r._clock_refresh_failures,r.clock_refresh_error)==(-1.,99,'unchanged-before-success')
results['two_slow_no_third_no_anchor']=True

for label,slot in [('wrong_peer',dict(peer=('192.168.50.3',8797))),
                   ('wrong_role',dict(role='untrusted_role')),('wrong_http',dict(status=302)),
                   ('bad_date',dict(date='invalid')),('first_deadline',dict(headers=3.1))]:
    f=fixture.Fixture([slot,FAST]);r=bind(f);outcome,_=run(r,f)
    assert outcome=='REJECTED' and len(f.calls)==1
    results[label+'_no_retry']=True

for label,mutation in [
    ('cancel',lambda f,r:setattr(f,'cancelled',True)),
    ('runtime_closed',lambda f,r:setattr(r,'closed',True)),
    ('runtime_started',lambda f,r:setattr(r,'started',True)),
    ('runtime_boot',lambda f,r:setattr(r,'boot_id','other-boot')),
    ('timeline_boot',lambda f,r:setattr(f.timeline,'boot_id','other-boot')),
    ('endpoint',lambda f,r:setattr(f.client,'host','192.168.50.3')),
    ('source_id',lambda f,r:setattr(f.timeline,'source_id','other-source')),
    ('source_sha',lambda f,r:setattr(f.timeline,'source_sha256','0'*64)),
    ('policy_sha',lambda f,r:setattr(f.timeline,'policy_sha256','0'*64)),
    ('full_policy',lambda f,r:f.timeline.policy.update(max_sample_age=3.)),
    ('fatal',lambda f,r:setattr(f.timeline,'fatal',True)),
    ('deadline_after_rejection',lambda f,r:setattr(f.mono,'value',104.)),
    ('fresh_revision_not_zero',lambda f,r:setattr(f.timeline,'file_revision',1)),
    ('clock_busy',lambda f,r:setattr(f.timeline,'pending_writers',1)),
    ('verifier',lambda f,r:setattr(f.timeline,'source_validator',lambda s:True)),
    ('runtime_clock',lambda f,r:setattr(r,'clock',lambda:104.)),
]:
    f=fixture.Fixture([SLOW,FAST]);r=bind(f,after_error=mutation);outcome,_=run(r,f)
    assert outcome=='REJECTED' and len(f.calls)==1,label
    results[label+'_no_second_GET']=True

class OtherClockUnavailable(ClockUnavailable):pass
for label,exc in [('typed_other_code',ClockUnavailable('http_date_conflicts_with_anchor')),
                  ('typed_subclass',OtherClockUnavailable('sample_rtt_exceeded')),
                  ('same_text_generic',RuntimeError('sample_rtt_exceeded'))]:
    f=fixture.Fixture([SLOW,FAST]);r=bind(f,replace_error=exc);outcome,_=run(r,f)
    assert outcome=='REJECTED' and len(f.calls)==1
    results[label+'_no_retry']=True

f=fixture.Fixture([FAST,SLOW,FAST]);f.anchored_ram_setup();f.fake_persistence(fail=False)
original=copy.deepcopy(f.timeline.anchor);r=bind(f);outcome,_=run(r,f)
assert outcome=='ACCEPTED' and len(f.calls)==2 and f.timeline.file_revision==9
assert all(f.timeline.anchor[k]==original[k] for k in ('anchor_monotonic','utc_estimate_at_anchor','base_uncertainty_seconds'))
results['persistent_anchor_rejection_receipt_plus_one_then_fresh_verify']=True

f=fixture.Fixture([FAST,SLOW,FAST]);f.anchored_ram_setup();f.fake_persistence(fail=True);r=bind(f)
outcome,exc=run(r,f)
assert outcome=='REJECTED' and exc.args==('sample_rtt_exceeded',) and len(f.calls)==1 and f.timeline.file_revision==7
results['hidden_anchor_revision_conflict_no_second_GET']=True

for label,mutation in [('anchor_changed',lambda f,r:f.timeline.anchor.update(base_uncertainty_seconds=99.)),
                       ('revision_plus_two',lambda f,r:setattr(f.timeline,'file_revision',9)),
                       ('path_changed',lambda f,r:setattr(f.timeline,'anchor_path',Path('OTHER_NEVER_OPENED.json')))]:
    f=fixture.Fixture([FAST,SLOW,FAST]);f.anchored_ram_setup();f.fake_persistence(fail=False)
    r=bind(f,after_error=mutation);outcome,_=run(r,f)
    assert outcome=='REJECTED' and len(f.calls)==1
    results[label+'_no_second_GET']=True

f=fixture.Fixture([FAST,dict(date='Mon, 02 Nov 2026 12:00:30 GMT'),FAST]);f.anchored_ram_setup();r=bind(f)
outcome,exc=run(r,f)
assert outcome=='REJECTED' and exc.args==('http_date_conflicts_with_anchor',) and len(f.calls)==1
results['direct_anchor_conflict_no_retry']=True

f=fixture.Fixture([FAST,SLOW,dict(date='Mon, 02 Nov 2026 12:00:30 GMT'),FAST]);f.anchored_ram_setup();f.fake_persistence(fail=False)
r=bind(f);outcome,exc=run(r,f)
assert outcome=='REJECTED' and exc.args==('http_date_conflicts_with_anchor',) and len(f.calls)==2
results['second_fresh_sample_anchor_conflict_immediate_no_third']=True

class FakeClient:
    def __init__(self,failure=None):self.count=0;self.failure=failure
    def sample_health_date(self,*args,**kwargs):
        self.count+=1
        if self.failure:raise self.failure
        return {'synthetic_first_success':True}
for success in (True,False):
    f=fixture.Fixture([]);r=bind(f);r.timeline=object();r.client=FakeClient(None if success else ClockUnavailable('sample_rtt_exceeded'))
    outcome,_=run(r,f)
    assert (outcome=='ACCEPTED')==success and r.client.count==1
    results['nonstandard_timeline_first_only_'+str(success)]=True

f=fixture.Fixture([FAST]);r=bind(f)
token_node=copy.deepcopy(next(n for n in ast.walk(klass) if isinstance(n,ast.FunctionDef) and n.name=='retry_token'))
token_ns={**ns,'self':r}
exec(compile(ast.Module(body=[token_node],type_ignores=[]),'<exact-local-token>','exec'),token_ns)
token=token_ns['retry_token']
before=(copy.deepcopy(f.timeline.anchor),copy.deepcopy(f.timeline.policy),f.timeline.file_revision,f.timeline.last_seen,
        f.timeline.status,f.timeline.last_error,f.timeline.fatal,f.timeline.pending_writers)
value=token();value['policy']['max_rtt']=999.
after=(copy.deepcopy(f.timeline.anchor),copy.deepcopy(f.timeline.policy),f.timeline.file_revision,f.timeline.last_seen,
       f.timeline.status,f.timeline.last_error,f.timeline.fatal,f.timeline.pending_writers)
assert before==after
results['local_token_readonly_detached_no_mono_or_save']=True

entered,finished=threading.Event(),threading.Event()
def locked_reader():entered.set();token();finished.set()
with f.timeline.lock:
    thread=threading.Thread(target=locked_reader);thread.start();assert entered.wait(1.)
    assert not finished.wait(.02)
assert finished.wait(1.);thread.join(1.)
results['local_token_uses_original_clock_lock']=True

f=fixture.Fixture([SLOW,FAST]);r=bind(f);factory=f.client.connection_factory;lock_checks=[]
def lock_checked_factory(*args,**kwargs):
    c=factory(*args,**kwargs);connect=c.connect
    def check_connect():
        acquired=[]
        def other_thread():
            ok=f.timeline.lock.acquire(timeout=.1);acquired.append(ok)
            if ok:f.timeline.lock.release()
        t=threading.Thread(target=other_thread);t.start();t.join(.5)
        assert acquired==[True]
        lock_checks.append(True);connect()
    c.connect=check_connect;return c
f.client.connection_factory=lock_checked_factory
outcome,_=run(r,f)
assert outcome=='ACCEPTED' and lock_checks==[True,True]
results['no_clock_lock_held_across_either_HTTP_transaction']=True

old=ast.parse((HERE/'baseline/board/runtime/board_business.py').read_text(encoding='utf-8'))
new=ast.parse(SOURCE.read_text(encoding='utf-8'))
old_cls=next(n for n in old.body if isinstance(n,ast.ClassDef) and n.name=='BoardBusinessRuntime')
new_cls=next(n for n in new.body if isinstance(n,ast.ClassDef) and n.name=='BoardBusinessRuntime')
idx=next(i for i,n in enumerate(new_cls.body) if isinstance(n,ast.FunctionDef) and n.name=='initialize_clock')
new_cls.body[idx]=copy.deepcopy(next(n for n in old_cls.body if isinstance(n,ast.FunctionDef) and n.name=='initialize_clock'))
assert ast.dump(old,include_attributes=False)==ast.dump(new,include_attributes=False)
results['whole_module_AST_only_initialize_clock_changed']=True

# Real original persistence in a new, explicitly synthetic local fixture. These
# paths cannot name a board/business anchor and are retained as review evidence.
def persistent_fixture(slots):
    directory=HERE/'synthetic_anchor_fixtures'/('t-'+uuid.uuid4().hex[:8])
    assert directory.resolve().is_relative_to(HERE.resolve())
    directory.mkdir(parents=True)
    anchor=directory/'synthetic.json'
    assert len(str(anchor))+22<260  # This Windows runtime lacks long-path os.open support.
    f=fixture.Fixture(slots,utc_bounds=(1793534400.,1793707200.),anchor_path=anchor)
    return f

f=persistent_fixture([FAST,SLOW,FAST]);f.anchored_ram_setup()
original=copy.deepcopy(f.timeline.anchor);revision=f.timeline.file_revision
r=bind(f);outcome,_=run(r,f)
assert outcome=='ACCEPTED' and len(f.calls)==2 and f.timeline.file_revision==revision+2
stored=json.loads(f.timeline.anchor_path.read_text(encoding='utf-8'))
assert stored['revision']==f.timeline.file_revision and stored['verification_status']=='verified'
assert all(f.timeline.anchor[k]==original[k] for k in ('anchor_monotonic','utc_estimate_at_anchor','base_uncertainty_seconds'))
results['original_persistent_save_receipt_and_new_verification_real_local_file']=True

f=persistent_fixture([FAST,SLOW,dict(**FAST,date='Mon, 02 Nov 2026 13:00:01 GMT')]);f.anchored_ram_setup()
original=copy.deepcopy(f.timeline.anchor);revision=f.timeline.file_revision
f.mono.value+=f.timeline.policy['verified_ttl']+.1
quality=f.timeline.quality_snapshot()
before_expiry=dict(quality_reason=quality['reason'],safe_for_compaction=quality['safe_for_compaction'],
                   status=f.timeline.status,last_error=f.timeline.last_error,fatal=f.timeline.fatal)
assert quality['reason']=='verification_expired' and not quality['safe_for_compaction']
assert (f.timeline.status,f.timeline.last_error,f.timeline.fatal)==('verified','',False)
r=bind(f);outcome,_=run(r,f)
after_quality=f.timeline.quality_snapshot()
assert outcome=='ACCEPTED' and len(f.calls)==2 and f.timeline.file_revision==revision+2
assert after_quality['quality']=='verified' and after_quality['safe_for_compaction']
assert all(f.timeline.anchor[k]==original[k] for k in ('anchor_monotonic','utc_estimate_at_anchor','base_uncertainty_seconds'))
results['naturally_expired_original_persistent_anchor_slow_then_fast_refresh']=True
expiry_receipt=dict(before=before_expiry,after=dict(quality=after_quality['quality'],
    safe_for_compaction=after_quality['safe_for_compaction'],status=f.timeline.status,
    last_error=f.timeline.last_error,fatal=f.timeline.fatal),
    candidate_changed_for_expiry=False,original_anchor_origin_and_uncertainty_preserved=True,
    original_max_rtt_seconds=f.timeline.policy['max_rtt'],two_requests_share_same_deadline=len(set(f.deadlines))==1)

f=persistent_fixture([FAST,SLOW,FAST]);f.anchored_ram_setup();revision=f.timeline.file_revision
other=fixture.clock_module.StableTimelineClock('synthetic-boot',f.client.health_date_source_id(),
    f.client.validate_sample,utc_bounds=(1793534400.,1793707200.),monotonic=f.mono,
    anchor_path=f.timeline.anchor_path)
assert other.file_revision==revision
other.save()  # A competing local synthetic writer advances only the fixture.
assert other.file_revision==revision+1 and f.timeline.file_revision==revision
r=bind(f);outcome,exc=run(r,f)
assert outcome=='REJECTED' and exc.args==('sample_rtt_exceeded',) and len(f.calls)==1
assert f.timeline.file_revision==revision
results['original_persistent_revision_conflict_swallowed_by_RTT_but_no_second_GET_real_local_file']=True

output=dict(schema='aura-initialize-clock-overlay-synthetic-validation-1',candidate_sha256=EXPECTED,
            case_count=len(results),all_cases_pass=True,cases=results,
            real_original_clock_and_client_used=True,only_exact_candidate_method_executed=True,
            persistence_hooks_and_original_local_synthetic_file_cases_both_used=True,
            natural_verified_TTL_expiry=expiry_receipt,
            local_synthetic_anchor_files_created_inside_independent_review=True,
            real_network_models_Store_business_anchor_files_devices_or_producer_accessed=False)
(HERE/'VALIDATION.json').write_text(json.dumps(output,indent=2),encoding='utf-8')
print(json.dumps({'candidate_sha256':EXPECTED,'cases':len(results),'all_cases_pass':True,
                  'whole_module_changed_only_initialize_clock':True,'no_real_network_Store_or_anchor':True}))
