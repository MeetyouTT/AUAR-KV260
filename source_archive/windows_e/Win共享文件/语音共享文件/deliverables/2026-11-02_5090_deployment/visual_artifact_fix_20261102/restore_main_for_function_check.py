"""Original UI main/listen preparation only; no motion or performance changes."""
import hashlib
import http.client
import json
import os
from pathlib import Path
import time
import traceback

BOOT='a6d4a069-e9b0-4065-8df7-dc23556b168e'
BASE=Path('/home/root/aura-5090-recovery-20261102-a6d4a069')
TX=BASE/'function-check-main-1'
OWNERS=[(394712,'3106155','48a28efa32b2050901e73e85a80a30a90dcfbce0b7249bde5d6d90902740631d'),(394720,'3106263','e81bf963d019b5b23293db8d863359ca706564b4e1fa74a69a212517dc08de48'),(362659,'2850120','acf3ee123d7674fdea6e90e79252909ca396249c870269169910879d940c27dd'),(394769,'3108205','236c51091fd21c314c0ca2e1cb48fefde1181eda5cb0431b974f60941dfa943e')]

def verify():
    assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==BOOT
    rows=[]
    for pid,birth,cmd in OWNERS:
        p=Path('/proc')/str(pid);s=p.joinpath('stat').read_text().rsplit(')',1)[1].split();actual=hashlib.sha256(p.joinpath('cmdline').read_bytes()).hexdigest()
        assert s[19]==birth and actual==cmd
        rows.append({'pid':pid,'birth_ticks':s[19],'command_sha256':actual})
    return rows

def request(path,body=None):
    c=http.client.HTTPConnection('127.0.0.1',8783,timeout=3)
    try:
        method='GET';headers={'Host':'127.0.0.1:8783','Origin':'http://127.0.0.1:8783'}
        if body is not None:method='POST';headers['Content-Type']='application/json';body=json.dumps(body).encode()
        c.request(method,path,body=body,headers=headers);r=c.getresponse();raw=r.read(2097153);assert r.status==200 and len(raw)<=2097152;return json.loads(raw)
    finally:c.close()

def receipt(name,value):
    fd=os.open(str(TX/name),os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
    with os.fdopen(fd,'wb') as f:f.write((json.dumps(value,sort_keys=True)+'\n').encode());f.flush();os.fsync(f.fileno())

def command(name,body):
    verify();receipt(name,{'body':body,'single_submission':True,'mono_ms':int(time.monotonic()*1000)});request('/api/command',body)

result={'schema':'aura-main-listening-other-function-check-1','boot_id':BOOT,'axis_commands_sent':0,'affinity_or_nice_changes':0,'source_model_or_threshold_changes':0,'errors':[]}
created=False;stage='verify'
try:
    result['owners']=verify()
    result['cancelled_affinity_transactions_absent']={name:not (BASE/name).exists() for name in ('single-consumer-affinity-1','single-consumer-affinity-fresh-2')}
    assert all(result['cancelled_affinity_transactions_absent'].values())
    v=request('/api/state');assert not (v.get('manual_pan') or {}).get('automatic_following'),'Axis needs exclusive STOP owner'
    TX.mkdir(mode=0o700);created=True;receipt('prepare-intent.json',{'main':True,'listening':True,'no_motion':True,'mono_ms':int(time.monotonic()*1000)})
    stage='main_page'
    if v.get('ui_page')!='main':command('main-page-intent.json',{'type':'ui_page','page':'main'})
    stage='normal_listening'
    v=request('/api/state')
    if not v['handsfree_dialogue']['enabled']:command('listen-intent.json',{'type':'conversation_toggle'})
    for _ in range(60):
        v=request('/api/state');h=v['handsfree_dialogue']
        if v.get('ui_page')=='main' and h['enabled'] and (h['microphone_open'] or v.get('playing') or v.get('pending_job')):break
        time.sleep(.2)
    result['owners_after']=verify();h=v['handsfree_dialogue'];pan=v.get('manual_pan') or {};rb=pan.get('readback') or {};speaker=(v.get('board_business') or {}).get('speaker') or {}
    result.update(mono_ms=int(time.monotonic()*1000),ui_sequence=v.get('sequence'),ui_page=v.get('ui_page'),listening_enabled=h.get('enabled'),microphone_open=h.get('microphone_open'),handsfree_state=h.get('state'),playing=bool(v.get('playing')),pending_job=bool(v.get('pending_job')),avatar_visible=(v.get('avatar_display') or {}).get('visible'),character_pair_ready=(v.get('character_pair') or {}).get('state')=='READY',runtime_fault_count=(v.get('runtime_faults') or {}).get('count'),axis={'state':pan.get('state'),'automatic_following':pan.get('automatic_following'),'error_present':bool(pan.get('error')),'pulse_us':pan.get('pulse_us'),'readback':{k:rb.get(k) for k in ('flags','lease_left_ms','width_us','active','armed')}},speaker={k:speaker.get(k) for k in ('conversation_address','identity_match_threshold','identity_ambiguity_margin','speaker_calibrated','ready','active','queued_or_active')})
    result['frontend_thread_settings']=[]
    for p in Path('/proc/394769/task').iterdir():
        try:
            tid=int(p.name);s=p.joinpath('stat').read_text().rsplit(')',1)[1].split();result['frontend_thread_settings'].append({'tid':tid,'birth_ticks':s[19],'nice':int(s[16]),'affinity':sorted(os.sched_getaffinity(tid))})
        except OSError:pass
    result['no_temporary_affinity_active']=all(z['affinity']==[0,1,2,3] and z['nice']==-10 for z in result['frontend_thread_settings'])
    result['ready_for_other_function_observation']=result['ui_page']=='main' and result['listening_enabled'] and (result['microphone_open'] or result['playing'] or result['pending_job']) and result['avatar_visible'] and result['character_pair_ready'] and result['runtime_fault_count']==0 and not pan.get('automatic_following') and result['no_temporary_affinity_active']
except Exception as exc:
    result['errors'].append({'stage':stage,'class':type(exc).__name__,'line':traceback.extract_tb(exc.__traceback__)[-1].lineno})
finally:
    if created:receipt('result.json',result)
    print(json.dumps(result))
