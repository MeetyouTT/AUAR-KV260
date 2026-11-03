"""Source-only retry assessment, not a production candidate.

Exact original client/clock execute only against fake HTTP sockets and an
in-memory clock. No device, HTTP request, model, Store or real anchor is opened.
The two-attempt wrapper below models the proposed rule solely for countercases.
"""
import ast
import copy
import hashlib
import http.client
import importlib.util
import json
import math
from pathlib import Path
import socket
import sys
import threading
import time

HERE = Path(__file__).resolve().parent
SOURCES = HERE.parent / 'current_public_source'
CLOCK_SOURCE = SOURCES / 'common/board_timeline_clock.py'
CLIENT_SOURCE = SOURCES / 'board/runtime/board_dialogue_client.py'
assert hashlib.sha256(CLOCK_SOURCE.read_bytes()).hexdigest() == '93b65ec3d9ca393b32499845297c78a2f1f71bc19e069b2ce3dc6f69e795af02'
assert hashlib.sha256(CLIENT_SOURCE.read_bytes()).hexdigest() == '600e044dedfc90c70e319e0e91999b8b4b7f648e0a5ca98e2a1bc0ab09a076b2'
spec = importlib.util.spec_from_file_location('original_clock_readonly_assessment', CLOCK_SOURCE)
clock_module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = clock_module
spec.loader.exec_module(clock_module)
ClockUnavailable = clock_module.ClockUnavailable
namespace = dict(http=http, json=json, math=math, socket=socket, threading=threading,
                 time=time, HttpDateSample=clock_module.HttpDateSample, MAX_HEALTH_BYTES=64*1024)
classes = [copy.deepcopy(n) for n in ast.parse(CLIENT_SOURCE.read_text(encoding='utf-8')).body
           if isinstance(n, ast.ClassDef) and n.name in
           ('ModelRequestError', '_RetainedSocket', '_ConnectionControl', 'InferenceHttpClient')]
exec(compile(ast.Module(body=classes, type_ignores=[]), '<exact-original-client-classes>', 'exec'), namespace)


class Mono:
    def __init__(self): self.value = 100.
    def __call__(self): return self.value


class FakeSocket:
    def __init__(self, peer): self.peer = peer
    def getpeername(self): return self.peer
    def shutdown(self, how): pass
    def close(self): pass


class Response:
    def __init__(self, slot):
        self.status = slot.get('status', 200)
        self.raw = json.dumps(dict(protocol_version=1, ok=True,
                                  role=slot.get('role', 'model_inference_only'))).encode()
        self.date = slot.get('date', 'Mon, 02 Nov 2026 12:00:00 GMT')
    def getheaders(self):
        return [('Date', self.date), ('Content-Type', 'application/json'), ('Content-Length', str(len(self.raw)))]
    def read(self, limit): return self.raw[:limit]
    def close(self): pass


class Connection:
    def __init__(self, owner, slot, host, port, timeout):
        self.owner, self.slot, self.sock = owner, slot, None
        self.peer = slot.get('peer', (host, port))
        owner.timeouts.append(timeout)
    def connect(self):
        self.owner.mono.value += self.slot.get('connect', .005)
        self.sock = FakeSocket(self.peer)
    def request(self, method, path, headers):
        assert method == 'GET' and path == '/health'
        self.owner.mono.value += self.slot.get('send', .001)
    def getresponse(self):
        self.owner.mono.value += self.slot.get('headers', .004)
        return Response(self.slot)
    def close(self):
        if self.sock: self.sock.close()


class Fixture:
    def __init__(self, slots, *, utc_bounds=(1793617200., 1793624400.), anchor_path=None):
        self.mono = Mono()
        self.slots = iter(slots)
        self.calls, self.timeouts, self.samples, self.deadlines = [], [], [], []
        self.cancelled = False
        def factory(host, port, *, timeout):
            slot = next(self.slots)
            self.calls.append(slot)
            return Connection(self, slot, host, port, timeout)
        self.client = namespace['InferenceHttpClient']('192.168.50.1', 8797,
                                                       clock=self.mono, connection_factory=factory)
        self.timeline = clock_module.StableTimelineClock('synthetic-boot', self.client.health_date_source_id(),
            self.client.validate_sample, utc_bounds=utc_bounds, monotonic=self.mono,
            anchor_path=anchor_path)
        original_observe = self.timeline.observe_http_date
        def observe(sample, **kwargs):
            self.samples.append(sample)
            return original_observe(sample, **kwargs)
        self.timeline.observe_http_date = observe
    def request(self, deadline):
        self.deadlines.append(deadline)
        return self.client.sample_health_date(self.timeline, deadline=deadline,
                                               cancelled=lambda: self.cancelled)
    def anchored_ram_setup(self):
        self.request(self.mono()+3.)
        self.calls.clear(); self.deadlines.clear(); self.timeouts.clear(); self.samples.clear()
    def fake_persistence(self, *, fail=False):
        # A sentinel Path is never passed to any filesystem operation. The exact
        # original observe_http_date calls only this replaced RAM hook.
        self.timeline.anchor_path = Path('SYNTHETIC_ANCHOR_NEVER_OPENED.json')
        self.timeline.file_revision = 7
        def persist():
            if fail: raise ClockUnavailable('anchor_revision_conflict')
            self.timeline.file_revision += 1
        self.timeline._save_locked = persist


def snapshot(f):
    t, c = f.timeline, f.client
    return dict(client=c, clock=c.clock, host=c.host, port=c.port, source=t.source_id, boot=t.boot_id,
                policy=copy.deepcopy(t.policy), source_sha=t.source_sha256, policy_sha=t.policy_sha256,
                anchor=copy.deepcopy(t.anchor), revision=t.file_revision, persistent=t.anchor_path is not None)


def model_retry_gate(f, before, exc, deadline):
    """Evaluation predicate only; not a proposed publisher-ready API."""
    t, c = f.timeline, f.client
    if type(exc) is not ClockUnavailable or exc.args != ('sample_rtt_exceeded',): return False
    if f.cancelled or f.mono() >= deadline or t.fatal: return False
    if (c is not before['client'] or c.clock is not before['clock'] or t.monotonic is not c.clock
            or (c.host, c.port) != (before['host'], before['port'])
            or t.source_id != before['source'] or t.boot_id != before['boot']
            or t.source_sha256 != before['source_sha'] or t.policy_sha256 != before['policy_sha']
            or t.policy != before['policy'] or t.anchor != before['anchor']): return False
    if before['anchor'] is not None and before['persistent']:
        # The original rejected-sample save validates the anchor and increments
        # revision. No increment means a hidden persistence error is possible.
        return t.file_revision == before['revision'] + 1
    return t.file_revision == before['revision']


def model_two_attempts(f, *, after_error=None):
    deadline = f.mono() + 3.
    before = snapshot(f)
    try:
        return f.request(deadline), 'ACCEPTED_FIRST'
    except Exception as exc:
        if after_error: after_error(f)
        if not model_retry_gate(f, before, exc, deadline):
            return type(exc).__name__ + ':' + str(exc), 'REJECTED_FIRST'
    try:
        return f.request(deadline), 'ACCEPTED_SECOND'
    except Exception as exc:
        return type(exc).__name__ + ':' + str(exc), 'REJECTED_SECOND'


SLOW = dict(connect=.6, send=.01, headers=.5)
FAST = dict(connect=.005, send=.001, headers=.004)
results = {}

f = Fixture([SLOW, FAST]); policy = copy.deepcopy(f.timeline.policy)
_, state = model_two_attempts(f)
assert state == 'ACCEPTED_SECOND' and len(f.calls) == 2
assert len(set(f.deadlines)) == 1 and f.timeline.policy == policy and policy['max_rtt'] == 1.
assert f.samples[0] is not f.samples[1] and f.client.validate_sample(f.samples[0]) is False
results['fresh_new_sample_after_RTT_only'] = dict(state=state, calls=len(f.calls), same_absolute_deadline=True,
    original_policy_unchanged=True, distinct_sample_objects=True, first_proof_cannot_be_replayed=True)

f = Fixture([FAST]); _, state = model_two_attempts(f)
assert state == 'ACCEPTED_FIRST' and len(f.calls) == 1
results['first_success_has_no_extra_request'] = dict(state=state, calls=len(f.calls))

f = Fixture([SLOW, SLOW, FAST]); _, state = model_two_attempts(f)
assert state == 'REJECTED_SECOND' and len(f.calls) == 2 and f.timeline.anchor is None
results['two_RTT_failures_no_third_or_anchor'] = dict(state=state, calls=len(f.calls), anchor_created=False)

for label, first in [('wrong_peer', dict(peer=('192.168.50.3',8797))),
                     ('wrong_role', dict(role='untrusted_role')),
                     ('invalid_date', dict(date='invalid')),
                     ('deadline', dict(headers=3.1))]:
    f = Fixture([first, FAST]); _, state = model_two_attempts(f)
    assert state == 'REJECTED_FIRST' and len(f.calls) == 1
    results[label] = dict(state=state, calls=len(f.calls))

for label, mutation in [('cancelled_after_first', lambda f:setattr(f,'cancelled',True)),
                        ('source_changed', lambda f:setattr(f.client,'host','192.168.50.3')),
                        ('boot_changed', lambda f:setattr(f.timeline,'boot_id','synthetic-other-boot')),
                        ('fatal_clock', lambda f:setattr(f.timeline,'fatal',True)),
                        ('deadline_consumed_after_first', lambda f:setattr(f.mono,'value',104.))]:
    f = Fixture([SLOW,FAST]); _, state=model_two_attempts(f,after_error=mutation)
    assert state == 'REJECTED_FIRST' and len(f.calls) == 1
    results[label]=dict(state=state,calls=len(f.calls))

f=Fixture([FAST,SLOW,FAST]);f.anchored_ram_setup();f.fake_persistence(fail=False)
original_anchor=copy.deepcopy(f.timeline.anchor);_,state=model_two_attempts(f)
assert state=='ACCEPTED_SECOND' and len(f.calls)==2 and f.timeline.file_revision==9
assert all(f.timeline.anchor[k]==original_anchor[k] for k in
           ('anchor_monotonic','utc_estimate_at_anchor','base_uncertainty_seconds'))
results['existing_anchor_rejection_persisted_then_fresh_verification']=dict(state=state,calls=len(f.calls),
    original_anchor_origin_and_uncertainty_unchanged=True,rejection_revision_receipt_present=True)

f=Fixture([FAST,SLOW,FAST]);f.anchored_ram_setup();f.fake_persistence(fail=True)
before=snapshot(f);deadline=f.mono()+3.
try:f.request(deadline)
except ClockUnavailable as exc:
    captured=exc
    assert exc.args==('sample_rtt_exceeded',) and f.timeline.last_error=='sample_rtt_exceeded'
else:raise AssertionError('Expected original RTT rejection')
naive=(type(captured) is ClockUnavailable and captured.args==('sample_rtt_exceeded',) and not f.timeline.fatal)
strict=model_retry_gate(f,before,captured,deadline)
assert naive and not strict and f.timeline.file_revision==7 and len(f.calls)==1
results['hidden_anchor_revision_conflict_counterexample']=dict(
    original_exception_code='sample_rtt_exceeded',original_last_error_code='sample_rtt_exceeded',
    original_clock_fatal=False,original_observe_swallowed_anchor_conflict=True,
    naive_code_only_gate_would_retry=True,strict_revision_receipt_gate_rejects=True,calls=len(f.calls))

f=Fixture([FAST,dict(date='Mon, 02 Nov 2026 12:00:30 GMT'),FAST]);f.anchored_ram_setup()
_,state=model_two_attempts(f)
assert state=='REJECTED_FIRST' and len(f.calls)==1
results['anchor_UTC_conflict_no_retry']=dict(state=state,calls=len(f.calls))

output=dict(schema='aura-original-date-retry-source-assessment-1',
    source_clock_sha256=hashlib.sha256(CLOCK_SOURCE.read_bytes()).hexdigest(),
    source_client_sha256=hashlib.sha256(CLIENT_SOURCE.read_bytes()).hexdigest(),
    evaluated_case_count=len(results),all_cases_pass=True,cases=results,
    wrapper_is_evaluation_model_not_production_candidate=True,
    exact_original_client_and_clock_used=True,
    real_network_devices_models_Store_anchorfiles_or_business_data_accessed=False,
    original_producer_or_production_sources_changed=False)
(HERE/'SYNTHETIC_ASSESSMENT.json').write_text(json.dumps(output,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'cases':len(results),'all_cases_pass':True,
                  'hidden_anchor_conflict_counterexample_reproduced':True,
                  'no_real_network_models_Store_anchor_files':True}))
