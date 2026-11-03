"""Root-scheduled two independent original Date samples; no model/DB/service writes.

Only public pinned source AST is loaded. HTTP timing and observation decorators
delegate unchanged to stdlib HTTPConnection and the exact original clock method.
No Date header, health body, exception message or source payload is printed.
"""
import argparse
import ast
import hashlib
import http.client
import json
from pathlib import Path
import sys
import time
import types

CLIENT_SHA='600e044dedfc90c70e319e0e91999b8b4b7f648e0a5ca98e2a1bc0ab09a076b2'
CLOCK_SHA='93b65ec3d9ca393b32499845297c78a2f1f71bc19e069b2ce3dc6f69e795af02'

def read_pinned(path,digest):
    assert path.is_file() and not path.is_symlink() and path.stat().st_size<1000000
    raw=path.read_bytes();assert hashlib.sha256(raw).hexdigest()==digest
    return raw.decode('utf-8')

def load_sources(aura,pins):
    assert pins['board/runtime/board_dialogue_client.py']==CLIENT_SHA
    assert pins['common/board_timeline_clock.py']==CLOCK_SHA
    timeline_source=read_pinned(aura/'common/board_timeline_clock.py',CLOCK_SHA)
    client_source=read_pinned(aura/'board/runtime/board_dialogue_client.py',CLIENT_SHA)
    timeline=types.ModuleType('_aura_original_timeline_probe')
    sys.modules[timeline.__name__]=timeline
    # This original module is all stdlib definitions. anchor_path stays None.
    exec(compile(ast.parse(timeline_source),'<pinned-original-board-timeline-clock>','exec'),timeline.__dict__)
    client_tree=ast.parse(client_source)
    client_tree.body=[node for node in client_tree.body if not (isinstance(node,ast.ImportFrom) and node.module and node.module.startswith('common.'))]
    client=types.ModuleType('_aura_original_client_probe')
    client.HttpDateSample=timeline.HttpDateSample
    sys.modules[client.__name__]=client
    # Model POST names are intentionally not imported and no request() is called.
    exec(compile(client_tree,'<pinned-original-board-dialogue-client>','exec'),client.__dict__)
    return client,timeline

def attempt(index,client_module,clock_module,boot,port,bounds):
    metadata={'attempt':index,'max_rtt_seconds':1.0,'original_total_deadline_seconds':3.0}
    timings={}
    class TimedHTTP(http.client.HTTPConnection):
        def connect(self):
            started=time.monotonic()
            try:return super().connect()
            finally:timings['connect_ms']=(time.monotonic()-started)*1000
        def request(self,*args,**kwargs):
            started=time.monotonic()
            try:return super().request(*args,**kwargs)
            finally:timings['request_ms']=(time.monotonic()-started)*1000
        def getresponse(self,*args,**kwargs):
            started=time.monotonic()
            try:
                result=super().getresponse(*args,**kwargs)
                metadata['http_status']=result.status
                return result
            finally:timings['response_headers_ms']=(time.monotonic()-started)*1000
    client=client_module.InferenceHttpClient('192.168.50.1',port,connection_factory=TimedHTTP)
    timeline=clock_module.StableTimelineClock(boot,client.health_date_source_id(),client.validate_sample,
        utc_bounds=tuple(bounds),anchor_path=None,monotonic=client.clock)
    assert timeline.policy['max_rtt']==1.0
    metadata['original_source_validator_bound']=timeline.source_validator==client.validate_sample
    original_observe=timeline.observe_http_date
    def observe(sample,**kwargs):
        timings['actual_sample_rtt_ms']=(sample.received_monotonic-sample.sent_monotonic)*1000
        timings['received_to_observe_ms']=(time.monotonic()-sample.received_monotonic)*1000
        metadata['original_sample_object_type']=type(sample) is clock_module.HttpDateSample
        metadata['original_verified_body_reached_observe']=True
        valid=False;plausible=False
        try:
            parsed=clock_module.parsedate_to_datetime(sample.date_header)
            valid=(bool(clock_module.DATE_FORMAT.fullmatch(sample.date_header)) and parsed.tzinfo is not None
                and parsed.utcoffset()==clock_module.timezone.utc.utcoffset(parsed)
                and clock_module.format_datetime(parsed,usegmt=True)==sample.date_header)
            plausible=bounds[0]<=parsed.timestamp()<=bounds[1]
        except (TypeError,ValueError,OverflowError):pass
        metadata['date_canonical_utc']=valid;metadata['date_within_configured_bounds']=plausible
        # Source proof is still live here and the original method consumes it.
        return original_observe(sample,**kwargs)
    timeline.observe_http_date=observe
    started=time.monotonic();cpu=time.process_time()
    try:
        client.sample_health_date(timeline,deadline=client.clock()+3.)
        metadata['result']='ORIGINAL_SAMPLE_ACCEPTED'
        metadata['clock_verified']=timeline.status=='verified'
    except Exception as exc:
        metadata['result']='ORIGINAL_SAMPLE_REJECTED'
        metadata['exception_type']=type(exc).__name__
        if isinstance(exc,clock_module.ClockUnavailable):
            value=str(exc)
            metadata['clock_error_code']=value if value in clock_module.ERROR_CODES else 'UNLISTED_REDACTED'
    finally:
        timings['total_wall_ms']=(time.monotonic()-started)*1000
        timings['total_process_cpu_ms']=(time.process_time()-cpu)*1000
    metadata['timings']=timings
    metadata['anchor_path_is_none']=timeline.anchor_path is None
    return metadata

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--boot-id',required=True)
    parser.add_argument('--startup-sha256',required=True)
    parser.add_argument('--startup-path',default='/home/root/aura-board-business-20261030/production-5259eab11e42af13/startup/config.json')
    args=parser.parse_args()
    assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==args.boot_id
    path=Path(args.startup_path);raw=path.read_bytes();assert hashlib.sha256(raw).hexdigest()==args.startup_sha256
    startup=json.loads(raw);assert len(startup['component_sha256'])==380
    aura=Path(startup['runtime'])/'aura';pins=startup['component_sha256']
    ui=json.loads(read_pinned(aura/'config/board_avatar_gtk.json',pins['config/board_avatar_gtk.json']))
    config=ui['board_business'];port=config.get('model_port',8797);assert port==8797
    bounds=config['utc_bounds'];assert len(bounds)==2
    client_module,clock_module=load_sources(aura,pins)
    attempts=[attempt(index,client_module,clock_module,args.boot_id,port,bounds) for index in (1,2)]
    assert path.read_bytes()==raw and Path('/proc/sys/kernel/random/boot_id').read_text().strip()==args.boot_id
    print(json.dumps({'status':'TWO_INDEPENDENT_ORIGINAL_DATE_PROBES_COMPLETED','attempts':attempts,
        'boot_id':args.boot_id,'startup_sha256':args.startup_sha256,
        'client_source_sha256':CLIENT_SHA,'clock_source_sha256':CLOCK_SHA,
        'instrumentation':'HTTPConnection timing subclass delegates unchanged; original timeline observe wrapper records metadata then invokes original.',
        'source_proof_or_rtt_policy_bypassed':False,'body_or_date_or_messages_exported':False,
        'models_db_services_camera_axis_or_persistent_anchor_touched':False}))

if __name__=='__main__':main()
