"""Bounded single-consumer affinity diagnostic with one fresh capture generation."""
import glob
import hashlib
import http.client
import json
import os
from pathlib import Path
import re
import struct
import time
import traceback

BOOT='a6d4a069-e9b0-4065-8df7-dc23556b168e'
STARTUP=Path('/home/root/aura-board-business-20261030/production-5259eab11e42af13/startup/config.json')
SHA='c3861fa3d2cbb10fee424804f7b3932eadd576819a2a6290c7ca406d900b9602'
OWNERS=[(394712,'3106155','48a28efa32b2050901e73e85a80a30a90dcfbce0b7249bde5d6d90902740631d'),(394720,'3106263','e81bf963d019b5b23293db8d863359ca706564b4e1fa74a69a212517dc08de48'),(362659,'2850120','acf3ee123d7674fdea6e90e79252909ca396249c870269169910879d940c27dd'),(394769,'3108205','236c51091fd21c314c0ca2e1cb48fefde1181eda5cb0431b974f60941dfa943e')]
WORKER=394769
TX=Path('/home/root/aura-5090-recovery-20261102-a6d4a069/single-consumer-affinity-fresh-2')

def verify():
    assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==BOOT
    assert hashlib.sha256(STARTUP.read_bytes()).hexdigest()==SHA
    for pid,birth,cmd in OWNERS:
        p=Path('/proc')/str(pid)
        assert p.joinpath('stat').read_text().rsplit(')',1)[1].split()[19]==birth
        assert hashlib.sha256(p.joinpath('cmdline').read_bytes()).hexdigest()==cmd
    assert os.getpriority(os.PRIO_PROCESS,WORKER)==-10

def request(port,path,body=None):
    c=http.client.HTTPConnection('127.0.0.1',port,timeout=2)
    try:
        headers={'Host':'127.0.0.1:'+str(port),'Origin':'http://127.0.0.1:'+str(port)}
        method='GET'
        if body is not None:
            method='POST';headers['Content-Type']='application/json';body=json.dumps(body).encode()
        t=time.monotonic_ns();c.request(method,path,body=body,headers=headers);r=c.getresponse();data=r.read(2097153)
        assert r.status==200 and len(data)<=2097152
        return json.loads(data),round((time.monotonic_ns()-t)/1e6,3)
    finally:c.close()

def ui():return request(8783,'/api/state')[0]

def receipt(name,value):
    fd=os.open(str(TX/name),os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
    with os.fdopen(fd,'wb') as f:f.write((json.dumps(value,sort_keys=True)+'\n').encode());f.flush();os.fsync(f.fileno())
    fd=os.open(str(TX),os.O_RDONLY|os.O_DIRECTORY)
    try:os.fsync(fd)
    finally:os.close(fd)

def command(name,body):
    verify();receipt(name,{'body':body,'mono_ms':int(time.monotonic()*1000),'single_submission':True})
    request(8783,'/api/command',body)

def listen(target,name):
    v=ui();h=v['handsfree_dialogue']
    if h['enabled']!=target:command(name,{'type':'conversation_toggle'})
    for _ in range(35):
        v=ui();h=v['handsfree_dialogue']
        if h['enabled']==target and h['microphone_open']==target:return v
        time.sleep(.2)
    raise RuntimeError('Listening transition unconfirmed')

def thread(tid):
    p=Path('/proc')/str(WORKER)/'task'/str(tid);s=(p/'stat').read_text().rsplit(')',1)[1].split()
    return {'tid':tid,'birth_ticks':s[19],'cpu_ticks':int(s[11])+int(s[12]),'nice':int(s[16]),'last_processor':int(s[36]),'affinity':sorted(os.sched_getaffinity(tid)),'policy':os.sched_getscheduler(tid)}

def threads():
    rows={}
    for p in (Path('/proc')/str(WORKER)/'task').iterdir():
        try:rows[int(p.name)]=thread(int(p.name))
        except OSError:pass
    return rows

def safe(v):
    cur=(v.get('audio_frontend') or {}).get('current') or {};diag=v.get('safe_capture_diagnostics') or {};q=diag.get('input_queue') or {};af=diag.get('audio_frontend') or {}
    numeric=lambda x:{k:z for k,z in x.items() if type(z) in (int,float,bool) and not any(w in k.lower() for w in ('score','probability','sample_value'))}
    code=diag.get('error_code');allowed=('','pcm_input_queue_overflow','pcm_input_reader_not_stopped','pcm_input_read_failed','frontend_error','frontend_auto_capture_failed')
    last=(v.get('audio_frontend') or {}).get('last_capture_failure') or {};last_af=last.get('audio_frontend') or {}
    return {'capture_failures':cur.get('capture_failures'),'worker_generation':cur.get('worker_generation'),'frontend':numeric(cur),'queue':numeric(q),'diagnostic_frontend':numeric(af),'error_code':code if code in allowed else ('OTHER_CODE' if code else ''),'last_failure_generation':last_af.get('worker_generation')}

def live(s,g=None):
    f=s['frontend'];q=s['queue']
    return (g is None or s['worker_generation']==g) and f.get('closed') is False and f.get('capture_lease_closed') is False and q.get('closed') is False and q.get('reader_alive') is True and type(f.get('frames')) is int

def proc(pid):
    p=Path('/proc')/str(pid);s=p.joinpath('stat').read_text().rsplit(')',1)[1].split();ss=[int(x) for x in p.joinpath('schedstat').read_text().split()]
    return {'cpu_ticks':int(s[11])+int(s[12]),'main_run_ns':ss[0],'main_wait_ns':ss[1]}

def header(preview):
    epoch=preview.get('camera_epoch');assert isinstance(epoch,str) and re.fullmatch('[0-9a-f]{32}',epoch)
    fd=os.open('/run/aura-camera-ui-'+epoch+'.frame',os.O_RDONLY|os.O_NOFOLLOW)
    with os.fdopen(fd,'rb') as f:
        magic,n=struct.unpack('!8sH',f.read(10));assert magic==b'AURABGR1' and 0<n<=1024;z=json.loads(f.read(n))
    assert z['board_boot_id']==BOOT and z['camera_epoch']==epoch
    return {'frame_id':z['frame_id'],'age_ms':int(time.monotonic()*1000)-z['captured_mono_ms']}

stage='preflight';applied=False;restored=False;ended=False;target=None;g=None;created=False;page_changed=False;old_page=None
result={'schema':'aura-fresh-generation-single-consumer-affinity-2','samples':[],'errors':[],'mask_seconds_limit':6,'nice_changes':0,'source_model_threshold_axis_changes':0,'audio_quality_passed':False,'physical_visual_improvement_claimed':False}
try:
    verify();v=ui();assert not v.get('playing') and not v.get('pending_job') and not v['manual_pan']['automatic_following'];old_page=v.get('ui_page');assert old_page in ('main','vision');TX.mkdir(mode=0o700);created=True
    receipt('probe-intent.json',{'original_page':old_page,'mono_ms':int(time.monotonic()*1000),'fixed_priority':-10,'seconds':6})
    stage='navigation'
    if old_page!='vision':command('vision-intent.json',{'type':'ui_page','page':'vision'});page_changed=True
    for _ in range(20):
        v=ui()
        if v.get('ui_page')=='vision':break
        time.sleep(.2)
    assert v.get('ui_page')=='vision'
    stage='fresh_capture'
    prior=listen(False,'initial-pause-intent.json');result['previous_capture_closed']=safe(prior)
    listen(True,'fresh-resume-intent.json')
    first=None
    for _ in range(50):
        v=ui();s=safe(v)
        if live(s):
            if first and s['worker_generation']==first['worker_generation'] and s['frontend']['frames']>first['frontend']['frames'] and s['queue'].get('frames_read',0)>first['queue'].get('frames_read',0):break
            first=s
        time.sleep(.2)
    else:raise RuntimeError('No advancing live capture generation')
    g=s['worker_generation'];failure0=s['capture_failures'];result['fresh_live_start']=s
    assert type(g)is int and type(failure0)is int
    stage='select_current_consumer';t=time.monotonic();a=threads();time.sleep(1);b=threads();dt=time.monotonic()-t;hz=os.sysconf('SC_CLK_TCK')
    hot=sorted([((x['cpu_ticks']-a[tid]['cpu_ticks'])/hz/dt*100,tid) for tid,x in b.items() if tid!=WORKER and tid in a and x['birth_ticks']==a[tid]['birth_ticks']],reverse=True)
    assert hot and hot[0][0]>20 and (len(hot)<2 or hot[1][0]<10)
    target=thread(hot[0][1]);tid=target['tid'];assert target['nice']==-10 and target['policy']==0 and target['affinity']==[0,1,2,3];core=target['last_processor'];assert core in target['affinity'];original_tids=set(b)
    result.update(target_before=target,chosen_cpu=core,worker_generation=g,clock_ticks_per_second=hz)
    def sample(tag):
        verify();nowthread=thread(tid);assert nowthread['birth_ticks']==target['birth_ticks'] and nowthread['nice']==-10;assert set(threads())==original_tids
        v,ms=request(8783,'/api/state');s=safe(v);assert live(s,g) and s['capture_failures']==failure0
        assert v.get('ui_page')=='vision' and v['handsfree_dialogue']['enabled'] and v['handsfree_dialogue']['microphone_open'] and not v['manual_pan']['automatic_following'] and not v.get('playing') and not v.get('pending_job')
        assert nowthread['affinity']==([core] if applied and not restored else target['affinity'])
        cam,cms=request(8790,'/v1/ui/status');face,fms=request(8790,'/v1/motion/face/observation');metrics=(v.get('ui_runtime') or {}).get('preview_metrics') or {};src=face.get('source_mono_ms');now=int(time.monotonic()*1000)
        result['samples'].append({'phase':tag,'mono_ms':now,'target':nowthread,'audio':s,'raw_header':header(cam.get('preview') or {}),'face_source_age_ms':now-src if type(src)is int else None,'face_ready':face.get('state')=='READY','displayed_frames':metrics.get('displayed_frames'),'request_ms':{'GUI':ms,'camera':cms,'face':fms},'GUI':proc(394720),'camera':proc(362659)})
    stage='baseline_all_cores'
    t=time.monotonic()
    while time.monotonic()-t<3:
        at=time.monotonic();sample('BASELINE_ALL4');time.sleep(max(0,.25-(time.monotonic()-at)))
    stage='affinity_six_seconds';receipt('affinity-intent.json',{'target':target,'selected_cpu':core,'generation':g,'mono_ms':int(time.monotonic()*1000)})
    assert thread(tid)['birth_ticks']==target['birth_ticks'];os.sched_setaffinity(tid,{core});applied=True;assert os.sched_getaffinity(tid)=={core}
    t=time.monotonic();result['affinity_start_mono_ms']=int(t*1000)
    while time.monotonic()-t<6:
        at=time.monotonic();sample('AFFINITY_ONE_CORE');time.sleep(max(0,.25-(time.monotonic()-at)))
    result['bounded_probe_complete']=True
except Exception as exc:
    result['errors'].append({'stage':stage,'class':type(exc).__name__,'line':traceback.extract_tb(exc.__traceback__)[-1].lineno})
finally:
    if applied:
        try:
            verify();nowthread=thread(target['tid'])
            if nowthread['birth_ticks']==target['birth_ticks']:
                os.sched_setaffinity(target['tid'],set(target['affinity']));restored=os.sched_getaffinity(target['tid'])==set(target['affinity']) and os.getpriority(os.PRIO_PROCESS,target['tid'])==-10
            else:ended=True
        except OSError:ended=True
        except Exception as exc:result['errors'].append({'stage':'restore_mask','class':type(exc).__name__,'line':traceback.extract_tb(exc.__traceback__)[-1].lineno})
    result.update(affinity_applied=applied,original_mask_restored=restored,target_lifetime_ended=ended,affinity_end_mono_ms=int(time.monotonic()*1000))
    if created:
        try:
            verify();result['after_before_pause']=safe(ui());closed=listen(False,'final-pause-intent.json');result['closed_capture']=safe(closed)
            result['closed_capture_matches_trial_generation']=g is not None and result['closed_capture']['worker_generation']==g
            resumed=listen(True,'final-resume-intent.json');result['listening_restored']=bool(resumed['handsfree_dialogue']['enabled'] and resumed['handsfree_dialogue']['microphone_open'])
            if page_changed and resumed.get('ui_page')=='vision':command('restore-page-intent.json',{'type':'ui_page','page':old_page})
            verify();result['IPC_main_nice_after']=os.getpriority(os.PRIO_PROCESS,WORKER)
        except Exception as exc:result['errors'].append({'stage':'close_capture_and_restore_UI','class':type(exc).__name__,'line':traceback.extract_tb(exc.__traceback__)[-1].lineno})
        result['final_stage']=stage;receipt('result.json',result)
    print(json.dumps(result))
