"""One quick read-only owner and idle-state check for performance measurement."""
import hashlib
import http.client
import json
import os
from pathlib import Path
import time
import traceback

BOOT='a6d4a069-e9b0-4065-8df7-dc23556b168e'
STARTUP=Path('/home/root/aura-board-business-20261030/production-5259eab11e42af13/startup/config.json')
EXPECTED_SHA='c3861fa3d2cbb10fee424804f7b3932eadd576819a2a6290c7ca406d900b9602'
OWNERS=[(394712,'3106155','48a28efa32b2050901e73e85a80a30a90dcfbce0b7249bde5d6d90902740631d'),(394720,'3106263','e81bf963d019b5b23293db8d863359ca706564b4e1fa74a69a212517dc08de48'),(362659,'2850120','acf3ee123d7674fdea6e90e79252909ca396249c870269169910879d940c27dd'),(394769,'3108205','236c51091fd21c314c0ca2e1cb48fefde1181eda5cb0431b974f60941dfa943e')]
out={'schema':'aura-performance-measurement-quick-readonly-check-1','control_write_count':0,'errors':[]}
try:
    out['boot_id']=Path('/proc/sys/kernel/random/boot_id').read_text().strip();assert out['boot_id']==BOOT
    out['startup_sha256']=hashlib.sha256(STARTUP.read_bytes()).hexdigest();assert out['startup_sha256']==EXPECTED_SHA
    out['owners']=[]
    for pid,birth,cmd in OWNERS:
        p=Path('/proc')/str(pid);s=p.joinpath('stat').read_text().rsplit(')',1)[1].split();actual=hashlib.sha256(p.joinpath('cmdline').read_bytes()).hexdigest()
        assert s[19]==birth and actual==cmd
        out['owners'].append({'pid':pid,'birth_ticks':s[19],'command_sha256':actual})
    out['state_gets']=0
    for attempt in range(11):
        c=http.client.HTTPConnection('127.0.0.1',8783,timeout=3)
        try:
            c.request('GET','/api/state');r=c.getresponse();raw=r.read(2097153);assert r.status==200 and len(raw)<=2097152;v=json.loads(raw);out['state_gets']+=1
        finally:c.close()
        speaker=(v.get('board_business') or {}).get('speaker') or {}
        busy=bool(v.get('playing') or v.get('pending_job') or speaker.get('active') or speaker.get('queued_or_active'))
        if not busy:break
        time.sleep(2)
    h=v.get('handsfree_dialogue') or {};pan=v.get('manual_pan') or {};rb=pan.get('readback') or {}
    out.update(mono_ms=int(time.monotonic()*1000),ui_page=v.get('ui_page'),ui_sequence=v.get('sequence'),listening_enabled=h.get('enabled'),microphone_open=h.get('microphone_open'),handsfree_state=h.get('state'),playing=bool(v.get('playing')),pending_job=bool(v.get('pending_job')),speaker_busy=busy,axis={'state':pan.get('state'),'automatic_following':pan.get('automatic_following'),'error_present':bool(pan.get('error')),'pulse_us':pan.get('pulse_us'),'readback':{k:rb.get(k) for k in ('flags','lease_left_ms','width_us','active','armed')}},runtime_fault_count=(v.get('runtime_faults') or {}).get('count'))
    out['frontend_thread_settings']=[]
    for p in Path('/proc/394769/task').iterdir():
        try:
            tid=int(p.name);s=p.joinpath('stat').read_text().rsplit(')',1)[1].split();out['frontend_thread_settings'].append({'tid':tid,'birth_ticks':s[19],'nice':int(s[16]),'affinity':sorted(os.sched_getaffinity(tid))})
        except OSError:pass
    out['original_thread_settings_preserved']=bool(out['frontend_thread_settings']) and all(z['nice']==-10 and z['affinity']==[0,1,2,3] for z in out['frontend_thread_settings'])
    out['ready_for_measurement']=not busy and out['ui_page']=='main' and out['listening_enabled'] is True and not pan.get('automatic_following') and rb.get('flags')==0 and rb.get('lease_left_ms')==0 and rb.get('active') is False and rb.get('armed') is False and out['runtime_fault_count']==0 and out['original_thread_settings_preserved']
except Exception as exc:
    out['errors'].append({'class':type(exc).__name__,'line':traceback.extract_tb(exc.__traceback__)[-1].lineno})
    out['ready_for_measurement']=False
print(json.dumps(out))
