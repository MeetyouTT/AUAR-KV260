"""Passive /proc + sysfs + filtered GET health sampling. No controls or imports."""
import datetime
import hashlib
import http.client
import json
import os
from pathlib import Path
import re
import time

DURATION = 40.0
INTERVAL = 2.0
HZ = os.sysconf('SC_CLK_TCK')
PAGE = os.sysconf('SC_PAGE_SIZE')
BOOT = Path('/proc/sys/kernel/random/boot_id').read_text().strip()
cache = {}

def numbers(value, depth=0):
    if depth > 6 or not isinstance(value,dict):
        return {}
    result = {}
    for key,item in value.items():
        if type(item) in (int,float,bool) or item is None:
            result[key] = item
        elif isinstance(item,dict):
            result[key] = numbers(item,depth+1)
    return result

def selected(value, keys):
    if not isinstance(value,dict):
        return {}
    return {k:value[k] for k in keys if k in value and (value[k] is None or type(value[k]) in (int,float,bool))}

def enum(value, allowed):
    return value if type(value) is str and value in allowed else None

def get(port,path):
    connection = http.client.HTTPConnection('127.0.0.1',port,timeout=2)
    started = time.monotonic()
    try:
        connection.request('GET',path)
        response = connection.getresponse()
        raw = response.read(2097153)
        assert response.status == 200 and len(raw) <= 2097152
        value = json.loads(raw)
        assert isinstance(value,dict)
        return value, (time.monotonic()-started)*1000
    finally:
        connection.close()

def health():
    output = {'monotonic':time.monotonic()}
    try:
        h, latency = get(8790,'/health')
        identity = h.get('identity') or {}
        schedule = h.get('dpu_schedule') or {}
        output['camera'] = dict(selected(h,('pid','capture_frames','detected_frames','capture_age_ms','observation_age_ms','motion_command_emitted')),
            get_latency_ms=latency,error_present=any(bool(h.get(k)) for k in ('camera_error','detector_error','preview_error')),
            identity_ready=identity.get('ready') is True,identity_error_present=bool(identity.get('error')),
            dpu_schedule=numbers(schedule),feature_inference=numbers(identity.get('feature_inference',{})))
        output['optional_recovery'] = {name:{'phase':enum((schedule.get('optional',{}).get(name,{}) or {}).get('recovery',{}).get('phase'),{'RUNNING','DISABLED','QUIESCING','RECOVERING','PROBING','FAULT','FENCED'})} for name in ('yunet','sface')}
    except (OSError,ValueError,AssertionError,http.client.HTTPException) as exc:
        output['camera_unavailable_error_type'] = type(exc).__name__
    try:
        g, latency = get(8783,'/api/state')
        hf = g.get('handsfree_dialogue') or {}
        pan = g.get('manual_pan') or {}
        business = g.get('board_business') or {}
        memory = business.get('memory') or {}
        output['gui'] = dict(selected(g,('sequence','playing','paused')),get_latency_ms=latency,
            ui_page=enum(g.get('ui_page'),{'main','vision','settings','history','profiles','memory','devices'}),
            phase=enum(g.get('phase'),{'IDLE','VOICE_PREPARING','VOICE_STARTING','SPEAKING','ACTION','DIALOGUE_WAITING'}),
            runtime_fault_count=selected(g.get('runtime_faults',{}),('count',)),
            avatar_display=numbers(g.get('avatar_display',{})),
            handsfree=dict(selected(hf,('enabled','microphone_open')),state=enum(hf.get('state'),{'PAUSED','WAITING_SERVICE','WAITING_SPEECH','WAITING_WAKE','COOLDOWN','CONVERSATION'})),
            pan=dict(selected(pan,('automatic_following','pulse_us','target_us','backend_pid')),
                state=enum(pan.get('state'),{'READY','MOVING','CONNECTING','FAULT','UNAVAILABLE','CLOSED','STOPPING'})),
            memory=dict(selected(memory,('running','completed','discarded')),error_present=bool(memory.get('error'))),
            retention=selected(business.get('retention',{}),('enabled','running')))
    except (OSError,ValueError,AssertionError,http.client.HTTPException) as exc:
        output['gui_unavailable_error_type'] = type(exc).__name__
    return output

def role(pid,birth,root):
    key = (pid,birth)
    if key in cache:
        return cache[key]
    comm = (root/'comm').read_text().strip()[:40]
    cmd = (root/'cmdline').read_bytes()
    mapping = (
        (b'run_face_motion.py','axis-follow'),(b'face_zone_editor','axis-boundary-editor'),
        (b'manual_process','axis-manual'),(b'board_avatar_gtk.py','avatar-GTK'),
        (b'board_avatar_pan','axis-manual'),(b'launcher.py','GUI-supervisor'),
        (b'camera_ui','camera-DPU'),(b'camera_server','camera-DPU'),
        (b'board_frontend_process','audio-frontend'),(b'board_capture','audio-capture'),
        (b'Xorg','Xorg'))
    label = next((label for fragment,label in mapping if fragment in cmd),comm)
    # Service PID membership is stronger than executable-name heuristics.
    if pid == CAMERA_PID: label = 'camera-DPU'
    if pid == GUI_PID: label = 'GUI-supervisor'
    if pid == GTK_PID: label = 'avatar-GTK'
    cache[key] = {'role':label,'comm':comm,'command_sha256':hashlib.sha256(cmd).hexdigest()}
    return cache[key]

def unit(name):
    # The kernel cgroup file supplies membership without invoking systemctl.
    return None

def pressure(name):
    path = Path('/proc/pressure')/name
    if not path.is_file(): return None
    output = {}
    for line in path.read_text().splitlines():
        label,*parts = line.split()
        output[label] = {key:float(value) for key,value in (part.split('=',1) for part in parts)}
    return output

def sample():
    started = time.monotonic()
    cpus = {}
    for line in Path('/proc/stat').read_text().splitlines():
        fields = line.split()
        if fields and re.fullmatch(r'cpu\d*',fields[0]):
            cpus[fields[0]] = list(map(int,fields[1:9]))
    memory = {}
    wanted = {'MemTotal','MemAvailable','MemFree','Buffers','Cached','Shmem','Slab','SReclaimable','SwapTotal','SwapFree','Dirty','Writeback','CmaTotal','CmaFree'}
    for line in Path('/proc/meminfo').read_text().splitlines():
        key,value = line.split(':',1)
        if key in wanted: memory[key] = int(value.split()[0])
    vm = {}
    for line in Path('/proc/vmstat').read_text().splitlines():
        key,value = line.split()
        if key in ('pgmajfault','pswpin','pswpout','oom_kill','allocstall_normal','allocstall_movable'):
            vm[key] = int(value)
    processes = {}
    for root in Path('/proc').iterdir():
        if not root.name.isdigit(): continue
        try:
            raw = (root/'stat').read_text().rsplit(')',1)[1].split()
            pid = int(root.name);birth = int(raw[19]);meta = role(pid,birth,root)
            processes[str(pid)] = dict(meta,birth_ticks=birth,cpu_ticks=int(raw[11])+int(raw[12]),rss_bytes=int(raw[21])*PAGE,threads=int(raw[17]),state=raw[0])
        except (FileNotFoundError,ProcessLookupError,PermissionError):
            continue
    temperatures = []
    for zone in sorted(Path('/sys/class/thermal').glob('thermal_zone*')):
        try:
            temperatures.append({'zone':zone.name,'type':(zone/'type').read_text().strip(), 'celsius':int((zone/'temp').read_text())/1000})
        except (OSError,ValueError): continue
    frequencies = {}
    for policy in sorted(Path('/sys/devices/system/cpu/cpufreq').glob('policy*')):
        entry = {}
        for key in ('scaling_cur_freq','scaling_min_freq','scaling_max_freq','cpuinfo_cur_freq'):
            try:entry[key] = int((policy/key).read_text())
            except (OSError,ValueError):pass
        frequencies[policy.name] = entry
    fs = os.statvfs('/')
    load_fields = Path('/proc/loadavg').read_text().split()
    return {'monotonic':started,'cpu_ticks':cpus,'memory_kib':memory,'vmstat':vm,'processes':processes,
        'load_average':list(map(float,load_fields[:3])),
        'pressure':{name:pressure(name) for name in ('cpu','memory','io')},
        'temperatures':temperatures,'frequencies_khz':frequencies,
        'root_filesystem':{'total_bytes':fs.f_blocks*fs.f_frsize,'available_bytes':fs.f_bavail*fs.f_frsize},
        'collection_ms':(time.monotonic()-started)*1000}

# Only metadata supplied by the host; no application code is loaded.
assert type(EXPECTED) is dict
CAMERA_PID = EXPECTED['camera_pid']
GUI_PID = EXPECTED['gui_pid']
GTK_PID = EXPECTED['gtk_pid']
startup = Path('/home/root/aura-board-business-20261030/production-5259eab11e42af13/startup/config.json')
startup_before = hashlib.sha256(startup.read_bytes()).hexdigest()
started_utc = datetime.datetime.now(datetime.timezone.utc).isoformat()
start = time.monotonic()
snapshots = []
health_samples = []
for index in range(21):
    deadline = start + index * INTERVAL
    if deadline > time.monotonic():time.sleep(deadline-time.monotonic())
    snapshots.append(sample())
    if index % 5 == 0:health_samples.append(health())
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip() == BOOT
print(json.dumps({'schema':'aura-passive-board-performance-1','boot_id':BOOT,'started_utc':started_utc,
    'finished_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'duration_seconds':snapshots[-1]['monotonic']-snapshots[0]['monotonic'],
    'clock_ticks_per_second':HZ,'observer_pid':os.getpid(),'expected_owners_from_handoff':EXPECTED,
    'startup_before_sha256':startup_before,'startup_after_sha256':hashlib.sha256(startup.read_bytes()).hexdigest(),
    'snapshots':snapshots,'health_samples':health_samples,
    'board_files_written':False,'database_opened':False,'models_or_audio_or_motion_triggered':False,
    'private_text_or_images_exported':False},sort_keys=True))
