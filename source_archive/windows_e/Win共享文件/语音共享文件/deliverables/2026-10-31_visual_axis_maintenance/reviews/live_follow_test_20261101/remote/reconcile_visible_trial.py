# USE_SESSION_COMMON
"""Reconcile the archived receipt label with the verified 80us profile, without repeating motion."""
current_guard();wide_active();verify_wide_files()
j=state();assert j['phase']=='VISIBLE_ROUNDTRIP_FAILED_NO_RETRY'
assert digest(ROOT/'bench_observed_80us_6s.py')==j['visible_script_sha256']=='3538bef649574da5607aa54ffbfdee5e103fc4f1db1ebb468eade239500b876c'
r=document(ROOT/'visible-80us-roundtrip.json')
assert r['status']=='20US_RETURN_ACK_AND_STOP_PASS_OBSERVATION_PENDING'
assert r['result']['commanded_sequence_us']==[1505,1585,1505] and r['result']['excursion_us']==80
assert r['automatic_repeat'] is False and len(r['events'])>=6
assert min(e['width_us'] for e in r['events'])==1505 and max(e['width_us'] for e in r['events'])==1585
sys.path.insert(0,str(RELEASE/'driver'))
from vsrv_driver import VSRVDriver
from vsrv_transport import NativeRegisters
m=document(RELEASE/'candidate-manifest.json')
with NativeRegisters(RELEASE/'driver/libvsrv.so',m['payload_files']['libvsrv.so'],BOOT,m['runtime_files']) as io:
    d=VSRVDriver(io,0x10282601,BOOT);now=d.status();assert now==r['result']['stopped']
assert now['flags']==0 and now['lease_left_ms']==0 and now['width_us']==1505
j.update(phase='VISIBLE_ROUNDTRIP_AWAITING_HUMAN',visible_receipt_sha256=digest(ROOT/'visible-80us-roundtrip.json'),
    current_stopped_readback=now,visible_receipt_label_is_archived_20us=True,actual_visible_excursion_us=80);save(j)
print(json.dumps(dict(status=j['phase'],commands=len(r['events']),sequence_us=r['result']['commanded_sequence_us'],
    actual_width_range_us=[1505,1585],stopped_readback=now,
    metadata_label_reconciled=True,motion_repeated=False,physical_observation='PENDING_USER')))
