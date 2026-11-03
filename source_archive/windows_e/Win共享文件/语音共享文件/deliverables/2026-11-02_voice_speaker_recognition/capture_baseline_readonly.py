"""Read only current source and public readiness metadata; no media or private DB."""
import base64
import hashlib
import http.client
import json
from pathlib import Path
import time
import traceback

STARTUP=Path('/home/root/aura-board-business-20261030/production-5259eab11e42af13/startup/config.json')
OWNERS=[(864526,'6036004','48a28efa32b2050901e73e85a80a30a90dcfbce0b7249bde5d6d90902740631d'),(864532,'6036118','db4a698acc249e1f85699e19fcfa3c0c430400cfc9cd99ee56bb814774350d37'),(362659,'2850120','acf3ee123d7674fdea6e90e79252909ca396249c870269169910879d940c27dd')]
TARGETS=('board/runtime/board_speaker_business.py','board/runtime/board_business.py','board/runtime/board_dialogue.py','board/runtime/board_memory_policy.py','common/speaker_identity.py','common/speaker_turns.py','tools/speaker_device.py','common/progressive_speaker.py')
out={'schema':'aura-speaker-R4-shared-source-readonly-baseline-1','mutations':0,'private_store_or_media_accessed':False,'errors':[]}
try:
    out['boot_id']=Path('/proc/sys/kernel/random/boot_id').read_text().strip();assert out['boot_id']=='a6d4a069-e9b0-4065-8df7-dc23556b168e'
    raw=STARTUP.read_bytes();out['startup_sha256']=hashlib.sha256(raw).hexdigest();assert out['startup_sha256']=='31d379389c2f2ac6d2e3ec33e49bd81f6f4076e4371a78f4ae7813a62193fbdf'
    cfg=json.loads(raw);aura=Path(cfg['runtime'])/'aura';pins=cfg['component_sha256'];assert len(pins)==380
    out.update(startup_path=str(STARTUP),runtime_source_root=str(aura),component_sha256=pins,startup_top_keys=sorted(cfg))
    out['owners']=[]
    for pid,birth,cmd in OWNERS:
        p=Path('/proc')/str(pid);s=p.joinpath('stat').read_text().rsplit(')',1)[1].split();actual=hashlib.sha256(p.joinpath('cmdline').read_bytes()).hexdigest();assert s[19]==birth and actual==cmd
        out['owners'].append({'pid':pid,'birth_ticks':s[19],'command_sha256':actual})
    out['sources']={};out['missing_optional_sources']=[]
    for name in TARGETS:
        p=aura/name
        if name not in pins or not p.is_file():out['missing_optional_sources'].append(name);continue
        data=p.read_bytes();sha=hashlib.sha256(data).hexdigest();assert sha==pins[name] and len(data)<1048576
        out['sources'][name]={'sha256':sha,'content_base64':base64.b64encode(data).decode('ascii')}
    c=http.client.HTTPConnection('127.0.0.1',8783,timeout=3)
    try:
        c.request('GET','/api/state');r=c.getresponse();data=r.read(2097153);assert r.status==200 and len(data)<=2097152;v=json.loads(data)
    finally:c.close()
    h=v.get('handsfree_dialogue') or {};pan=v.get('manual_pan') or {};rb=pan.get('readback') or {};speaker=(v.get('board_business') or {}).get('speaker') or {}
    out['current_state']={'ui_page':v.get('ui_page'),'phase':v.get('phase'),'avatar_visible':(v.get('avatar_display') or {}).get('visible'),'pair_ready':(v.get('character_pair') or {}).get('state')=='READY','runtime_fault_count':(v.get('runtime_faults') or {}).get('count'),'listening_enabled':h.get('enabled'),'microphone_open':h.get('microphone_open'),'handsfree_state':h.get('state'),'playing':bool(v.get('playing')),'pending_job':bool(v.get('pending_job')),'speaker_busy':bool(speaker.get('active') or speaker.get('queued_or_active')),'axis':{'state':pan.get('state'),'automatic_following':pan.get('automatic_following'),'error_present':bool(pan.get('error')),'readback':{k:rb.get(k) for k in ('flags','lease_left_ms','width_us','active','armed')}},'speaker_settings':{k:speaker.get(k) for k in ('identity_match_threshold','identity_ambiguity_margin','enrollment_consistency','speaker_calibrated','ready')}}
    out['mono_ms']=int(time.monotonic()*1000)
    out['source_unchanged_during_capture']=hashlib.sha256(STARTUP.read_bytes()).hexdigest()==out['startup_sha256'];assert out['source_unchanged_during_capture']
except Exception as exc:out['errors'].append({'class':type(exc).__name__,'line':traceback.extract_tb(exc.__traceback__)[-1].lineno})
print(json.dumps(out))
