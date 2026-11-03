import collections
import json
import math
from pathlib import Path

HERE = Path(__file__).resolve().parent
source = max(HERE.glob('BOARD_PERFORMANCE_*.json'),key=lambda p:p.stat().st_mtime_ns)
data = json.loads(source.read_text(encoding='utf-8'))['board_result']
samples = data['snapshots']
duration = samples[-1]['monotonic']-samples[0]['monotonic']
cores = len(samples[0]['cpu_ticks'])-1
hz = data['clock_ticks_per_second']

def stats(values):
    values = [x for x in values if type(x) in (int,float)]
    if not values:return None
    ordered = sorted(values)
    return {'mean':sum(values)/len(values),'min':min(values),'max':max(values),'p95':ordered[max(0,math.ceil(.95*len(values))-1)]}

cpu_intervals = []
per_core = collections.defaultdict(list)
processes = {}
total_ticks = busy_ticks = wait_ticks = 0
for before,after in zip(samples,samples[1:]):
    elapsed = after['monotonic']-before['monotonic']
    for name,new in after['cpu_ticks'].items():
        if name not in before['cpu_ticks']:continue
        delta = [b-a for a,b in zip(before['cpu_ticks'][name],new)]
        total = sum(delta)
        if total<=0 or min(delta)<0:continue
        busy = total-delta[3]-delta[4]
        value = busy*100/total
        if name == 'cpu':
            total_ticks += total;busy_ticks += busy;wait_ticks += delta[4]
            cpu_intervals.append({'start_monotonic':before['monotonic'],'duration_seconds':elapsed,'busy_percent_of_board':value,'iowait_percent':delta[4]*100/total})
        else:per_core[name].append(value)
    for pid,new in after['processes'].items():
        old = before['processes'].get(pid)
        if old is None or old['birth_ticks'] != new['birth_ticks']:continue
        ticks = new['cpu_ticks']-old['cpu_ticks']
        if ticks<0:continue
        key = (pid,new['birth_ticks'])
        row = processes.setdefault(key,{'pid':int(pid),'birth_ticks':new['birth_ticks'],'role':new['role'],'comm':new['comm'],'cpu_ticks':0,'peak_percent_one_core':0,'max_rss_mib':0,'max_threads':0})
        row['cpu_ticks'] += ticks
        row['peak_percent_one_core'] = max(row['peak_percent_one_core'],ticks/hz/elapsed*100)
        row['max_rss_mib'] = max(row['max_rss_mib'],old['rss_bytes']/1048576,new['rss_bytes']/1048576)
        row['max_threads'] = max(row['max_threads'],new['threads'])
for row in processes.values():
    row['average_percent_one_core'] = row['cpu_ticks']/hz/duration*100
    row['average_percent_of_board'] = row['average_percent_one_core']/cores
top = sorted(processes.values(),key=lambda x:x['cpu_ticks'],reverse=True)
memory = {key:stats([s['memory_kib'].get(key) for s in samples]) for key in ('MemTotal','MemAvailable','SwapTotal','SwapFree','CmaTotal','CmaFree','Dirty','Writeback')}
vm_delta = {key:samples[-1]['vmstat'][key]-value for key,value in samples[0]['vmstat'].items() if key in samples[-1]['vmstat']}
health = data['health_samples']
camera = [h for h in health if 'camera' in h]
gui = [h for h in health if 'gui' in h]
camera_summary = {'samples_available':len(camera)}
if len(camera)>1:
    first,last = camera[0],camera[-1]
    dt = last['monotonic']-first['monotonic']
    for key in ('capture_frames','detected_frames'):
        start,end = first['camera'].get(key),last['camera'].get(key)
        if type(start) is int and type(end) is int and first['camera'].get('pid')==last['camera'].get('pid'):
            camera_summary[key+'_delta'] = end-start
            camera_summary[key+'_per_second'] = (end-start)/dt
    for key in ('primary_calls','primary_period_overruns'):
        start = first['camera']['dpu_schedule'].get(key)
        end = last['camera']['dpu_schedule'].get(key)
        if type(start) is int and type(end) is int:
            camera_summary[key+'_delta'] = end-start
            camera_summary[key+'_cumulative_end'] = end
    camera_summary.update(
        error_observed=any(h['camera'].get('error_present') or h['camera'].get('identity_error_present') for h in camera),
        owner_fenced_observed=any(h['camera']['dpu_schedule'].get('owner_fenced') is True for h in camera),
        quiesced_observed=any(h['camera']['dpu_schedule'].get('quiesced') is True for h in camera),
        identity_ready_all=all(h['camera'].get('identity_ready') is True for h in camera),
        capture_age_ms=stats([h['camera'].get('capture_age_ms') for h in camera]),
        observation_age_ms=stats([h['camera'].get('observation_age_ms') for h in camera]),
        get_latency_ms=stats([h['camera'].get('get_latency_ms') for h in camera]))
gui_summary = {'samples_available':len(gui)}
if gui:
    gui_summary.update(
        observed_pages=sorted(set(str(h['gui'].get('ui_page')) for h in gui)),
        observed_phases=sorted(set(str(h['gui'].get('phase')) for h in gui)),
        listening_enabled_samples=sum(h['gui']['handsfree'].get('enabled') is True for h in gui),
        microphone_open_samples=sum(h['gui']['handsfree'].get('microphone_open') is True for h in gui),
        playback_active_samples=sum(h['gui'].get('playing') is True for h in gui),
        axis_follow_active_samples=sum(h['gui']['pan'].get('automatic_following') is True for h in gui),
        memory_running_samples=sum(h['gui']['memory'].get('running') is True for h in gui),
        memory_error_samples=sum(h['gui']['memory'].get('error_present') is True for h in gui),
        runtime_fault_count=[h['gui']['runtime_fault_count'].get('count') for h in gui],
        get_latency_ms=stats([h['gui'].get('get_latency_ms') for h in gui]),
        avatar_visible_samples=sum(h['gui']['avatar_display'].get('visible') is True for h in gui))
    start,end = gui[0]['gui']['memory'].get('completed'),gui[-1]['gui']['memory'].get('completed')
    if type(start) is int and type(end) is int and end>=start:
        gui_summary['memory_completed_delta'] = end-start
temperatures = collections.defaultdict(list)
for sample in samples:
    for zone in sample['temperatures']:temperatures[zone['type']].append(zone['celsius'])
summary = {
    'source_receipt':source.name,'started_utc':data['started_utc'],'finished_utc':data['finished_utc'],
    'duration_seconds':duration,'sample_count':len(samples),'cpu_cores':cores,
    'startup_changed_during_observation':data['startup_before_sha256']!=data['startup_after_sha256'],
    'system_cpu_busy_percent':dict(stats([x['busy_percent_of_board'] for x in cpu_intervals]),weighted_mean=busy_ticks*100/total_ticks),
    'system_cpu_iowait_percent':wait_ticks*100/total_ticks,
    'per_core_cpu_busy_percent':{key:stats(value) for key,value in per_core.items()},
    'memory_kib':memory,'vmstat_deltas':vm_delta,
    'load_average_start':samples[0]['load_average'],'load_average_end':samples[-1]['load_average'],
    'top_processes_cpu':top[:15],
    'observer_process':next((x for x in top if x['pid']==data['observer_pid']),None),
    'temperatures_celsius':{key:stats(value) for key,value in temperatures.items()},
    'cpu_frequency_khz_start':samples[0]['frequencies_khz'],'cpu_frequency_khz_end':samples[-1]['frequencies_khz'],
    'pressure_start':samples[0]['pressure'],'pressure_end':samples[-1]['pressure'],
    'root_filesystem_end':samples[-1]['root_filesystem'],
    'collection_time_ms':stats([s['collection_ms'] for s in samples]),
    'camera':camera_summary,'gui':gui_summary,
    'limits':['Passive current-workload observation; no ASR, recording or inference load was started.',
        'Process CPU normalized to full board capacity; one-core CPU is supplied separately.',
        'Short-lived processes between snapshots can be missed in per-process attribution.',
        'No hardware DPU utilization percentage or board power meter was read.'],
    'board_controls_sent':False}
destination = HERE/('SUMMARY_'+source.stem.removeprefix('BOARD_PERFORMANCE_')+'.json')
with destination.open('x',encoding='utf-8') as stream:
    json.dump(summary,stream,indent=2);stream.write('\n')
print(json.dumps(summary))
