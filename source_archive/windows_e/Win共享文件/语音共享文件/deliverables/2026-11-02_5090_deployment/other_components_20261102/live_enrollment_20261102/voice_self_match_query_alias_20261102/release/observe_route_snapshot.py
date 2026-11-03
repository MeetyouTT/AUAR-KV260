"""Only fixed route metadata; never export ASR text, identities or audio."""
import hashlib
import http.client
import json
from pathlib import Path
import time

ROOT=Path('/home/root/aura-board-business-20261030/production-5259eab11e42af13')
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip() == 'a6d4a069-e9b0-4065-8df7-dc23556b168e'
assert hashlib.sha256((ROOT/'startup/config.json').read_bytes()).hexdigest() == '44e8f154c9dd72d3b7619160f7a2dac64fda529daba91a96a196c12f68c8a295'
TRACE_BOOLS=set('observed reset_since_trace asr_result_seen speaker_requested enrollment_checked enrollment_active handler_available handler_called parser_code_known parser_face_only_const parser_voice_only_const has_register has_voiceprint has_voice has_warming has_face has_my_name has_level has_i_want has_i_would_like has_a_bit has_voice_word has_identity has_name_word face_active_before face_active_after speaker_state_known speaker_present_before speaker_active_before speaker_present_after speaker_active_after'.split())
TRACE_INTS={'version','asr_characters','business_turn_calls'}
TRACE_ENUMS={
 'binding_kind':set('not_evaluated ordinary remember_self name_hint invalid_name face_only voice_only other'.split()),
 'capability':set('not_selected explicit_memory_commands identity_enrollment identity_query speaker_identity structured_visual_query reasoning_dialogue ordinary_dialogue'.split()),
 'handler_result':set('not_called calling error none returned'.split()),
 'business_turn_result':set('not_called calling error none reply'.split()),
 'outcome':set('started complete rejected error'.split()),
 'phase':set('entered business_turn producer error finished'.split()),
 'input_mode':{'none','voice','face'},'resolved_mode':{'none','voice','face'},
 'error_class':set('none other BoardCapabilityNotReady StaleGeneration TimeoutError PermissionError ValueError RuntimeError OSError ConnectionError ModelRequestError ReplyRejected ScopeDenied StaleTurn InterruptedError MemoryError'.split())}
def trace(v):
    if type(v) is not dict:return None
    out={}
    for k,x in v.items():
        if k in TRACE_BOOLS and type(x) is bool:out[k]=x
        elif k in TRACE_INTS and type(x) is int:out[k]=min(4097,max(0,x))
        elif k in TRACE_ENUMS and type(x) is str:out[k]=x if x in TRACE_ENUMS[k] else 'other'
    return out
def get():
    c=http.client.HTTPConnection('127.0.0.1',8783,timeout=3)
    try:
        c.request('GET','/api/state');r=c.getresponse();raw=r.read(2097153)
        assert r.status==200 and len(raw)<=2097152
        return json.loads(raw)
    finally:c.close()
samples=[]; start=time.monotonic()
for index in range(1):
    v=get();b=v.get('board_business') or {};d=b.get('dialogue') or {};f=d.get('voice_enrollment') or {};h=v.get('handsfree_dialogue') or {};s=b.get('speaker') or {};route=d.get('last_voice_route') or {}
    samples.append(dict(elapsed=round(time.monotonic()-start,2),
        listening_enabled=h.get('enabled') is True,microphone_open=h.get('microphone_open') is True,
        playing=v.get('playing') is True,pending_job=bool(v.get('pending_job')),
        entry_mode=f.get('entry_mode') if f.get('entry_mode') in ('voice','face') else None,
        entry_name_pending=f.get('entry_name_pending') is True,enrollment_active=f.get('active') is True,
        speaker_ready=s.get('ready') is True,speaker_active=s.get('active') is True,
        route_generation=route.get('generation') if type(route.get('generation')) is int else None,
        route_trace=trace(route.get('entry_trace')),handler_trace=trace(f.get('entry_trace')),
        runtime_fault_count=(v.get('runtime_faults') or {}).get('count')))
    if False:time.sleep(1)
print(json.dumps(dict(schema='aura-live-entry-route-metadata-1',samples=samples,raw_text_or_identity_values_exported=False,board_mutations=False)))
