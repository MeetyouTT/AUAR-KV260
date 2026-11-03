"""Observe fixed self-match progress, without speech text or identity values."""
import hashlib
import http.client
import json
from pathlib import Path
import time

ROOT=Path('/home/root/aura-board-business-20261030/production-5259eab11e42af13')
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()=='a6d4a069-e9b0-4065-8df7-dc23556b168e'
assert hashlib.sha256((ROOT/'startup/config.json').read_bytes()).hexdigest()=='44e8f154c9dd72d3b7619160f7a2dac64fda529daba91a96a196c12f68c8a295'
PHASES={'IDLE','PROCESSING','COLLECTING','CANDIDATE','EXPIRED','CANCELLED','INSUFFICIENT_SPEECH','NO_CANDIDATE','NO_ENROLLMENT','SOURCE_CHANGED','UNAVAILABLE'}
def boolean(v):return v if type(v) is bool else None
def integer(v,maximum):return min(maximum,max(0,v)) if type(v) is int else None
samples=[];started=time.monotonic()
for index in range(1):
    c=http.client.HTTPConnection('127.0.0.1',8783,timeout=3)
    try:
        c.request('GET','/api/state');r=c.getresponse();raw=r.read(2097153)
        assert r.status==200 and len(raw)<=2097152
        v=json.loads(raw)
    finally:c.close()
    b=v.get('board_business') or {};s=b.get('speaker') or {};p=s.get('self_match_probe') or {};h=v.get('handsfree_dialogue') or {};d=b.get('dialogue') or {};route=d.get('last_voice_route') or {};face=d.get('voice_enrollment') or {}
    probe={k:boolean(p.get(k)) for k in ('completed_is_historical','field_calibrated','identity_verified','personal_memory_allowed')}
    probe.update(version=integer(p.get('version'),1),phase=p.get('phase') if p.get('phase') in PHASES else None,
        distinct_captures=integer(p.get('distinct_captures'),3),required_captures=integer(p.get('required_captures'),3),candidate_completed=integer(p.get('candidate_completed'),65535))
    samples.append(dict(elapsed=round(time.monotonic()-started,2),self_match_probe=probe,
        listening_enabled=boolean(h.get('enabled')),microphone_open=boolean(h.get('microphone_open')),
        playing=boolean(v.get('playing')),pending_job=bool(v.get('pending_job')),speaker_ready=boolean(s.get('ready')),
        speaker_active=boolean(s.get('active')),enrollment_active=boolean(face.get('active')),
        speaker_calibrated=boolean(s.get('speaker_calibrated')),automatic_profile_access=boolean(s.get('automatic_profile_access')),
        route_generation=integer(route.get('generation'),1000000000),
        runtime_fault_count=integer((v.get('runtime_faults') or {}).get('count'),100000)))
    if False:time.sleep(1)
print(json.dumps(dict(schema='aura-self-match-fixed-observation-1',samples=samples,board_mutations=False,
    identity_names_ids_scores_embeddings_audio_images_transcripts_exported=False)))
