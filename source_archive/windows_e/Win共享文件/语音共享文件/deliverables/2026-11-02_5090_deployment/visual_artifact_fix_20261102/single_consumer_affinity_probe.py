"""Same source/page, original listening ON/OFF/ON; metadata only, no motion."""
import glob
import hashlib
import http.client
import json
import os
from pathlib import Path
import re
import struct
import time

BOOT = 'a6d4a069-e9b0-4065-8df7-dc23556b168e'
STARTUP = Path('/home/root/aura-board-business-20261030/production-5259eab11e42af13/startup/config.json')
SHA = 'c3861fa3d2cbb10fee424804f7b3932eadd576819a2a6290c7ca406d900b9602'
OWNERS = [
    (394712, '3106155', '48a28efa32b2050901e73e85a80a30a90dcfbce0b7249bde5d6d90902740631d'),
    (394720, '3106263', 'e81bf963d019b5b23293db8d863359ca706564b4e1fa74a69a212517dc08de48'),
    (362659, '2850120', 'acf3ee123d7674fdea6e90e79252909ca396249c870269169910879d940c27dd'),
]
TX = Path('/home/root/aura-5090-recovery-20261102-a6d4a069/single-consumer-affinity-1')

def verify():
    assert Path('/proc/sys/kernel/random/boot_id').read_text().strip() == BOOT
    assert hashlib.sha256(STARTUP.read_bytes()).hexdigest() == SHA
    for pid, birth, command in OWNERS:
        p = Path('/proc') / str(pid)
        assert p.joinpath('stat').read_text().rsplit(')', 1)[1].split()[19] == birth
        assert hashlib.sha256(p.joinpath('cmdline').read_bytes()).hexdigest() == command

def request(port, path, body=None):
    c = http.client.HTTPConnection('127.0.0.1', port, timeout=2)
    try:
        headers = {'Origin': 'http://127.0.0.1:' + str(port), 'Host': '127.0.0.1:' + str(port)}
        method = 'GET'
        if body is not None:
            method = 'POST'
            headers['Content-Type'] = 'application/json'
            body = json.dumps(body).encode()
        before = time.monotonic_ns()
        c.request(method, path, body=body, headers=headers)
        r = c.getresponse()
        data = r.read(2097153)
        assert r.status == 200 and len(data) <= 2097152
        return json.loads(data), round((time.monotonic_ns() - before) / 1e6, 3)
    finally:
        c.close()

def ui():
    return request(8783, '/api/state')[0]

def intent(name, value):
    p = TX / name
    fd = os.open(str(p), os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, 'wb') as f:
        f.write((json.dumps(value, sort_keys=True) + '\n').encode())
        f.flush()
        os.fsync(f.fileno())
    fd = os.open(str(TX), os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)

def listening(target, name):
    verify()
    v = ui()
    assert not v.get('playing') and not v.get('pending_job')
    assert not (v.get('manual_pan') or {}).get('automatic_following')
    h = v['handsfree_dialogue']
    sent = False
    if h['enabled'] != target:
        intent(name, {'target_enabled': target, 'single_original_toggle': True, 'mono_ns': time.monotonic_ns()})
        request(8783, '/api/command', {'type': 'conversation_toggle'})
        sent = True
    for _ in range(15):
        v = ui()
        h = v['handsfree_dialogue']
        if h['enabled'] == target and h['microphone_open'] == target:
            return sent
        time.sleep(.2)
    raise RuntimeError('Listening transition requires GET-only reconciliation')

def process(pid):
    p = Path('/proc') / str(pid)
    values = p.joinpath('stat').read_text().rsplit(')', 1)[1].split()
    result = {'utime_ticks': int(values[11]), 'stime_ticks': int(values[12]), 'threads': int(values[17])}
    if p.joinpath('schedstat').is_file():
        ss = [int(x) for x in p.joinpath('schedstat').read_text().split()]
        result.update(main_thread_runtime_ns=ss[0], main_thread_runqueue_ns=ss[1], main_thread_slices=ss[2])
    return result

def system():
    result = {}
    for pattern, label in [('/sys/devices/system/cpu/cpu*/cpufreq/scaling_cur_freq', 'frequency_khz'),
                           ('/sys/class/thermal/thermal_zone*/temp', 'temperature_millidegrees')]:
        rows = {}
        for path in glob.glob(pattern):
            try:
                key = Path(path).parent.parent.name if label == 'frequency_khz' else Path(path).parent.name
                rows[key] = int(Path(path).read_text().strip())
            except (OSError, ValueError):
                pass
        result[label] = rows
    return result

def header(preview):
    epoch = preview.get('camera_epoch')
    assert isinstance(epoch, str) and re.fullmatch('[0-9a-f]{32}', epoch)
    p = Path('/run') / ('aura-camera-ui-' + epoch + '.frame')
    fd = os.open(str(p), os.O_RDONLY | os.O_NOFOLLOW)
    with os.fdopen(fd, 'rb') as f:
        prefix = f.read(10)
        magic, count = struct.unpack('!8sH', prefix)
        assert magic == b'AURABGR1' and 0 < count <= 1024
        value = json.loads(f.read(count))  # Pixel bytes are never read.
    assert value['board_boot_id'] == BOOT and value['camera_epoch'] == epoch
    now = int(time.monotonic() * 1000)
    return {'frame_id': value['frame_id'], 'captured_mono_ms': value['captured_mono_ms'],
            'raw_header_age_ms': now - value['captured_mono_ms']}

WORKER=394769;WORKER_BIRTH='3108205';WORKER_COMMAND='236c51091fd21c314c0ca2e1cb48fefde1181eda5cb0431b974f60941dfa943e'
def worker():
 p=Path('/proc')/str(WORKER);assert p.joinpath('stat').read_text().rsplit(')',1)[1].split()[19]==WORKER_BIRTH;assert hashlib.sha256(p.joinpath('cmdline').read_bytes()).hexdigest()==WORKER_COMMAND
def thread(tid):
 p=Path('/proc')/str(WORKER)/'task'/str(tid);v=(p/'stat').read_text().rsplit(')',1)[1].split();return {'tid':tid,'birth_ticks':v[19],'utime_ticks':int(v[11]),'stime_ticks':int(v[12]),'nice':int(v[16]),'last_processor':int(v[36]),'affinity':sorted(os.sched_getaffinity(tid)),'policy':os.sched_getscheduler(tid)}
def threads():
 rows={}
 for p in (Path('/proc')/str(WORKER)/'task').iterdir():
  try:rows[int(p.name)]=thread(int(p.name))
  except (OSError,ProcessLookupError):pass
 return rows
def safe(v):
 cur=(v.get('audio_frontend') or {}).get('current') or {};diag=v.get('safe_capture_diagnostics') or {};q=diag.get('input_queue') or {};af=diag.get('audio_frontend') or {}
 keys=('frame_bytes','capacity_frames','capacity_ms','queued_frames','peak_frames','frames_read','frames_delivered','source_read_mean_ms','source_read_max_ms','queue_mean_ms','queue_max_ms','closed','reader_alive','cancelled')
 nums=lambda x:{k:z for k,z in x.items() if type(z) in (int,float,bool) and not any(w in k.lower() for w in ('score','probability','sample_value'))}
 code=diag.get('error_code');code=code if code in ('','pcm_input_queue_overflow','pcm_input_reader_not_stopped','pcm_input_read_failed','frontend_error','frontend_auto_capture_failed') else ('OTHER_CODE' if code else '')
 return {'capture_failures':cur.get('capture_failures'),'worker_generation_cache':cur.get('worker_generation'),'frontend_cached_numeric':nums(cur),'diagnostic_queue_cache':{k:q[k] for k in keys if k in q},'diagnostic_frontend_cache':nums(af),'diagnostic_error_code':code,'local_recording_state':(v.get('local_recording') or {}).get('state'),'handsfree_state':(v.get('handsfree_dialogue') or {}).get('state')}
verify();worker();v=ui();assert v.get('ui_page')=='vision' and not v.get('playing') and not v.get('pending_job') and not v['manual_pan']['automatic_following'];assert v['handsfree_dialogue']['enabled'] and v['handsfree_dialogue']['microphone_open'];assert os.getpriority(os.PRIO_PROCESS,WORKER)==-10
start,a=time.monotonic(),threads();time.sleep(1);b=threads();duration=time.monotonic()-start;hz=os.sysconf('SC_CLK_TCK');hot=[]
for tid,x in b.items():
 old=a.get(tid)
 if tid!=WORKER and old and old['birth_ticks']==x['birth_ticks']:
  cpu=((x['utime_ticks']+x['stime_ticks'])-(old['utime_ticks']+old['stime_ticks']))/hz/duration*100;hot.append((cpu,tid))
assert hot;hot.sort(reverse=True);assert hot[0][0]>20 and (len(hot)<2 or hot[1][0]<10),'No unique active DSP consumer'
tid=hot[0][1];target=thread(tid);assert target['nice']==-10 and target['policy']==0 and target['affinity']==[0,1,2,3];core=target['last_processor'];assert core in target['affinity'];baseline=safe(ui());base_fail=baseline['capture_failures'];TX.mkdir(mode=0o700)
intent('affinity-intent.json',{'worker_pid':WORKER,'worker_birth':WORKER_BIRTH,'target':target,'selected_cpu':core,'seconds':6,'nice_changed':False});samples=[];applied=False;restored=False;target_exited=False;reason='elapsed';errors=[]
try:
 worker();assert thread(tid)['birth_ticks']==target['birth_ticks'];os.sched_setaffinity(tid,{core});applied=True;assert os.sched_getaffinity(tid)=={core} and os.getpriority(os.PRIO_PROCESS,tid)==-10
 t0=time.monotonic();original_tids=set(b)
 while time.monotonic()-t0<6:
  loop=time.monotonic();worker()
  try:nowthread=thread(tid)
  except OSError:target_exited=True;reason='target_lifetime_ended';break
  if nowthread['birth_ticks']!=target['birth_ticks']:reason='target_lifetime_changed';break
  current=threads()
  if set(current)!=original_tids:reason='thread_set_changed';break
  assert nowthread['nice']==-10 and nowthread['affinity']==[core] and os.getpriority(os.PRIO_PROCESS,WORKER)==-10
  v,ms=request(8783,'/api/state');status=safe(v)
  if v.get('ui_page')!='vision' or v.get('playing') or v.get('pending_job') or v['manual_pan']['automatic_following']:reason='UI_or_activity_changed';break
  if not v['handsfree_dialogue']['enabled'] or not v['handsfree_dialogue']['microphone_open']:reason='listening_changed';break
  if type(base_fail) is int and type(status['capture_failures']) is int and status['capture_failures']>base_fail:reason='new_capture_failure';break
  cam,cms=request(8790,'/v1/ui/status');obs,fms=request(8790,'/v1/motion/face/observation');now=int(time.monotonic()*1000);metric=(v.get('ui_runtime') or {}).get('preview_metrics') or {};src=obs.get('source_mono_ms')
  samples.append({'mono_ms':now,'target_thread':nowthread,'audio_status':status,'raw_header':header(cam.get('preview') or {}),'face_source_age_ms':now-src if type(src)is int else None,'displayed_frames':metric.get('displayed_frames'),'projection_frame_visible':metric.get('frame_visible'),'request_ms':{'GUI':ms,'camera':cms,'face':fms},'GUI_process':process(394720),'camera_process':process(362659)})
  time.sleep(max(0.,.25-(time.monotonic()-loop)))
except Exception as exc:errors.append(type(exc).__name__);reason='exception'
finally:
 if applied:
  try:
   worker();nowthread=thread(tid)
   if nowthread['birth_ticks']==target['birth_ticks']:
    os.sched_setaffinity(tid,set(target['affinity']));restored=os.sched_getaffinity(tid)==set(target['affinity']) and os.getpriority(os.PRIO_PROCESS,tid)==-10
   else:target_exited=True
  except (OSError,ProcessLookupError):target_exited=True
verify();worker();assert restored or target_exited
after_before_pause=safe(ui())
# Close only through the normal UI to obtain the just-closed capture diagnostic.
was_enabled=ui()['handsfree_dialogue']['enabled'];pause_sent=False;resume_sent=False
if was_enabled:
 intent('close-capture-intent.json',{'single_original_pause':True});request(8783,'/api/command',{'type':'conversation_toggle'});pause_sent=True
for _ in range(20):
 v=ui()
 if not v['handsfree_dialogue']['enabled'] and not v['handsfree_dialogue']['microphone_open']:break
 time.sleep(.2)
closed=safe(v);assert not v['handsfree_dialogue']['enabled'] and not v['handsfree_dialogue']['microphone_open']
intent('restore-listening-intent.json',{'single_original_resume':True});request(8783,'/api/command',{'type':'conversation_toggle'});resume_sent=True
for _ in range(20):
 v=ui()
 if v['handsfree_dialogue']['enabled'] and v['handsfree_dialogue']['microphone_open']:break
 time.sleep(.2)
verify();worker();assert v['handsfree_dialogue']['enabled'] and v['handsfree_dialogue']['microphone_open'];assert os.getpriority(os.PRIO_PROCESS,WORKER)==-10
result={'schema':'aura-single-DSP-affinity-six-second-probe-1','status':'SHORT_AFFINITY_PROBE_FINISHED_OR_ABORTED_ORIGINAL_MASK_RESTORED','target_before':target,'chosen_cpu':core,'target_applied':applied,'original_mask_restored':restored,'target_lifetime_ended':target_exited,'reason':reason,'errors_fixed_classes':errors,'IPC_main_nice_after':os.getpriority(os.PRIO_PROCESS,WORKER),'no_nice_model_source_axis_or_threshold_change':True,'listening_restored':True,'original_pause_and_resume_after_probe':{'pause':pause_sent,'resume':resume_sent},'before_cache':baseline,'after_before_pause_cache':after_before_pause,'closed_capture_diagnostic':closed,'samples':samples,'cached_queue_is_not_realtime':True,'audio_quality_passed':False,'physical_visual_improvement_claimed':False}
intent('affinity-result.json',result);print(json.dumps(result))
