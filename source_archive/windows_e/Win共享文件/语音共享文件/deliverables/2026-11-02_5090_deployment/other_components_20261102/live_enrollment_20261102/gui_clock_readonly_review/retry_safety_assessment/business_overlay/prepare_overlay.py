"""Build an isolated one-method overlay; never touches a producer or board file."""
import ast
import difflib
import hashlib
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
BASE=HERE.parents[1]/'current_public_source/board/runtime/board_business.py'
raw=BASE.read_bytes()
assert hashlib.sha256(raw).hexdigest()=='b08209eca7979825e26845080bca5e1d64e065d3cabd1178df763a93540573f2'
source=raw.decode('utf-8')
tree=ast.parse(source)
cls=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='BoardBusinessRuntime')
old=next(n for n in cls.body if isinstance(n,ast.FunctionDef) and n.name=='initialize_clock')
replacement='''    def initialize_clock(self, *, timeout=3., cancelled=lambda: False):
        if type(timeout) not in (int, float) or not 0 < timeout <= 10:
            raise ValueError('Use a bounded explicit Date sample')
        deadline = self.clock() + timeout
        def retry_token():
            timeline, client = self.timeline, self.client
            if type(timeline) is not StableTimelineClock or type(client) is not InferenceHttpClient:
                return None
            # Metadata only. Never retain this clock lock over HTTP or file IO.
            with timeline.lock:
                return dict(timeline=timeline, client=client, runtime_boot=self.boot_id,
                    runtime_clock=self.clock, boot=timeline.boot_id, source=timeline.source_id,
                    source_sha=timeline.source_sha256, policy_sha=timeline.policy_sha256,
                    monotonic=timeline.monotonic, verifier=timeline.source_validator,
                    path=timeline.anchor_path, endpoint=(client.host, client.port),
                    client_clock=client.clock, configured=(self.config.model_host, self.config.model_port),
                    policy=copy.deepcopy(timeline.policy), anchor=copy.deepcopy(timeline.anchor),
                    revision=timeline.file_revision, status=timeline.status, error=timeline.last_error,
                    fatal=timeline.fatal,
                    busy=(timeline.active_compactions, timeline.pending_writers, timeline.deferred_rejection))
        before = retry_token()
        try:
            result = self.client.sample_health_date(self.timeline, deadline=deadline, cancelled=cancelled)
        except ClockUnavailable as exc:
            if type(exc) is not ClockUnavailable or exc.args != ('sample_rtt_exceeded',):
                raise
            after = retry_token()
            if before is None or after is None or self.started or self.closed:
                raise
            objects = ('timeline', 'client', 'runtime_clock', 'monotonic', 'client_clock')
            unchanged = ('runtime_boot', 'boot', 'source', 'source_sha', 'policy_sha', 'verifier',
                         'path', 'endpoint', 'configured', 'policy', 'anchor')
            if (any(after[key] is not before[key] for key in objects)
                    or any(after[key] != before[key] for key in unchanged)
                    or before['fatal'] or after['fatal']
                    or before['busy'] != (0, 0, '') or after['busy'] != (0, 0, '')
                    or (before['status'], before['error']) not in
                       (('uninitialized', 'uninitialized'), ('verified', ''), ('rejected', 'sample_rtt_exceeded'))
                    or (after['status'], after['error']) != ('rejected', 'sample_rtt_exceeded')
                    or after['boot'] != after['runtime_boot']
                    or after['monotonic'] is not after['runtime_clock']
                    or after['client_clock'] is not after['runtime_clock']
                    or after['endpoint'] != after['configured']
                    or after['verifier'] != self.client.validate_sample
                    or after['source'] != self.client.health_date_source_id()
                    or after['policy'].get('max_rtt') != 1.):
                raise
            if before['anchor'] is None:
                if before['revision'] != 0 or after['revision'] != 0:
                    raise
            elif before['path'] is not None:
                # observe_http_date suppresses a rejection-save error. Only an
                # exact revision increment proves that original save succeeded.
                if after['revision'] != before['revision'] + 1:
                    raise
            elif after['revision'] != before['revision']:
                raise
            if cancelled() or self.clock() >= deadline:
                raise
            # New original-client transaction, proof and socket; never replay
            # a rejected sample, extend its deadline or retry another failure.
            result = self.client.sample_health_date(self.timeline, deadline=deadline, cancelled=cancelled)
        self._clock_refresh_next = self.clock() + 600.
        self._clock_refresh_failures = 0
        self.clock_refresh_error = ''
        return result
'''
lines=source.splitlines(keepends=True)
candidate=''.join(lines[:old.lineno-1])+replacement+''.join(lines[old.end_lineno:])
path=HERE/'candidate/board/runtime/board_business.py';path.parent.mkdir(parents=True,exist_ok=True)
path.write_bytes(candidate.encode('utf-8'))
baseline=HERE/'baseline/board/runtime/board_business.py';baseline.parent.mkdir(parents=True,exist_ok=True);baseline.write_bytes(raw)
(HERE/'CANDIDATE.diff').write_text(''.join(difflib.unified_diff(source.splitlines(True),candidate.splitlines(True),
    fromfile='a/board/runtime/board_business.py',tofile='b/board/runtime/board_business.py')),encoding='utf-8')
manifest={'schema':'aura-initialize-clock-retry-overlay-local-1','production_or_producer_changed':False,
 'files':{'board/runtime/board_business.py':{'before_sha256':hashlib.sha256(raw).hexdigest(),
 'after_sha256':hashlib.sha256(path.read_bytes()).hexdigest()}},
 'changed_methods':['BoardBusinessRuntime.initialize_clock'],'clock_source_changed':False,
 'client_source_changed':False,'max_transactions':2,'production_total_deadline_seconds':3.,
 'max_accepted_sample_rtt_seconds':1.,'requires_typed_original_RTT_error_and_verified_metadata':True}
(HERE/'SOURCE_MANIFEST.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
print(json.dumps(manifest))
