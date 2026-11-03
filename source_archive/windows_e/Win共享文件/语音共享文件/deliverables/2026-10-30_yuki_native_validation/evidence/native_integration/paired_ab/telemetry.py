"""Read-only numeric telemetry. Never exports identity or conversation payloads."""
from pathlib import Path
import os,re,time,urllib.request,json

HZ=os.sysconf('SC_CLK_TCK')
LAST_CAMERA_PID=None
CONTAINERS={'camera','capture','video','detector','detection','tracking','tracker','identity','face','recognition',
 'dpu','yolox','stats','health','status','runtime','metrics','performance','pipeline','worker','native','counters','source','pipeline_metrics','dpu_schedule'}
LEAVES={'pid','fps','hz','rate','frames','frame_count','captured','published','processed','dropped','errors',
 'error_count','ready','active','alive','sequence','frame_sequence','frame_id','latency_ms','inference_ms','capture_ms',
 'capture_frames','detected_frames','preview_frames','capture_age_ms','observation_age_ms','capture_hz','detection_hz','preview_hz','observation_frame_id','last_inference_ms'}
DENY={'identity_id','face_id','track_id','target_id','name','label','fingerprint','embedding','template','reply','text','transcript','heard'}

def camera_metrics():
    result={}
    try:
        with urllib.request.urlopen('http://127.0.0.1:8790/health',timeout=.4) as response:root=json.load(response)
        def walk(value,path='',depth=0):
            if not isinstance(value,dict) or depth>6:return
            for key,item in value.items():
                if key in DENY:continue
                name=path+'.'+key if path else key
                if isinstance(item,dict) and key in CONTAINERS:walk(item,name,depth+1)
                elif key in LEAVES and isinstance(item,(int,float,bool)):result[name]=item
                elif key in ('state','status') and item in ('READY','RUNNING','ACTIVE','ERROR','STOPPED','DEGRADED'):result[name]=item
        walk(root)
        for key in ('camera_error','detector_error','preview_error'):
            if key in root:result[key+'_present']=bool(root[key])
        return {'numeric':result,'available':True}
    except Exception as error:return {'available':False,'error_type':type(error).__name__}

def live_ui_metrics():
    try:
        with urllib.request.urlopen('http://127.0.0.1:8783/api/state',timeout=.7) as response:value=json.load(response)
        portrait=value.get('portrait_offload',{});display=value.get('avatar_display',{});settings=value.get('ui_settings',{})
        return {'available':True,'portrait':{k:portrait[k] for k in ('mode','selected','target_fps','fallback_fps') if k in portrait},
          'display':{k:display[k] for k in ('kind','fps','age_ms') if k in display},
          'settings':{k:settings[k] for k in ('economy','fullscreen') if k in settings},'playing':bool(value.get('playing')),'paused':bool(value.get('paused'))}
    except Exception as error:return {'available':False,'error_type':type(error).__name__}

def cpu_system():
    row=Path('/proc/stat').read_text().splitlines()[0].split()[1:9]
    values=[int(x) for x in row];return {'total_ticks':sum(values),'busy_ticks':sum(values)-values[3]-values[4],'hz':HZ,'cores':os.cpu_count()}

def all_process_stats():
    result={}
    for path in Path('/proc').iterdir():
        if not path.name.isdigit():continue
        try:
            raw=(path/'stat').read_text();values=raw[raw.rfind(')')+2:].split()
            result[int(path.name)]={'ppid':int(values[1]),'cpu_ticks':int(values[11])+int(values[12])}
        except (OSError,ValueError,IndexError):continue
    return result

def family_pids(root_pid,processes):
    found={int(root_pid)};changed=True
    while changed:
        next_set=found|{pid for pid,data in processes.items() if data['ppid'] in found}
        changed=next_set!=found;found=next_set
    return sorted(pid for pid in found if pid in processes)

def process_memory(pid):
    result={'rss_kib':None,'pss_kib':None,'rss_high_water_kib':None}
    try:
        status=Path('/proc',str(pid),'status').read_text()
        for line in status.splitlines():
            key,_,value=line.partition(':')
            if key=='VmRSS':result['rss_kib']=int(value.split()[0])
            if key=='VmHWM':result['rss_high_water_kib']=int(value.split()[0])
        for line in Path('/proc',str(pid),'smaps_rollup').read_text().splitlines():
            if line.startswith('Pss:'):result['pss_kib']=int(line.split()[1])
    except (OSError,ValueError):pass
    return result

def gpu_metrics(pids=()):
    root=Path('/sys/kernel/debug/mali');result={'utilization_unit':'UNVERIFIED_RAW_DEBUGFS_VALUE','processes':{}}
    for name in ('utilization_gp','utilization_pp','utilization_gp_pp'):
        try:result[name+'_raw']=float((root/name).read_text().strip())
        except (OSError,ValueError):result[name+'_raw']=None
    try:
        raw=(root/'gpu_memory').read_text()
        match=re.search(r'Mali mem usage:\s*(\d+)',raw);result['global_mali_bytes']=int(match.group(1)) if match else None
        family=set(pids)
        for line in raw.splitlines():
            match=re.fullmatch(r'\s*(.*?)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s*',line)
            if match:
                pid=int(match.group(2))
                if pid in family:result['processes'][str(pid)]=dict(zip(('mali_bytes','peak_mali_bytes','external_bytes','ump_bytes','dma_bytes'),map(int,match.groups()[2:])))
        result['family_mali_bytes']=sum(v['mali_bytes'] for v in result['processes'].values())
    except (OSError,ValueError):result['global_mali_bytes']=result['family_mali_bytes']=None
    return result

def system_memory():
    data={}
    for line in Path('/proc/meminfo').read_text().splitlines():
        key,_,value=line.partition(':')
        if key in ('MemTotal','MemFree','MemAvailable','Buffers','Cached','SwapTotal','SwapFree','CmaTotal','CmaFree'):data[key+'_kib']=int(value.split()[0])
    return data

def net_bytes():
    result={}
    for line in Path('/proc/net/dev').read_text().splitlines()[2:]:
        interface,_,values=line.partition(':');v=values.split()
        if interface.strip()!='lo':result[interface.strip()]={'rx_bytes':int(v[0]),'tx_bytes':int(v[8]),'rx_drops':int(v[3]),'tx_drops':int(v[11])}
    return result

def environment():
    values={}
    for path in Path('/sys/class/thermal').glob('thermal_zone*/temp'):
        try:values[str(path)]=float(path.read_text().strip())
        except (OSError,ValueError):pass
    for path in Path('/sys/devices/system/cpu').glob('cpu[0-9]*/cpufreq/scaling_cur_freq'):
        try:values[str(path)]=int(path.read_text().strip())
        except (OSError,ValueError):pass
    return values

def snapshot(root_pid,include_camera=True):
    global LAST_CAMERA_PID
    started=time.monotonic();processes=all_process_stats();pids=family_pids(root_pid,processes)
    memory={str(pid):process_memory(pid) for pid in pids}
    result={'at':started,'cpu_system':cpu_system(),'family_pids':pids,'family_cpu_ticks':sum(processes[pid]['cpu_ticks'] for pid in pids),
      'process_memory':memory,'family_rss_kib':sum(v['rss_kib'] or 0 for v in memory.values()),
      'family_pss_kib':sum(v['pss_kib'] or 0 for v in memory.values()) if all(v['pss_kib'] is not None for v in memory.values()) else None,
      'memory_system':system_memory(),'network':net_bytes(),'gpu':gpu_metrics(pids),'camera':camera_metrics() if include_camera else None,'environment':environment(),
      'collector_cpu_ticks':processes.get(os.getpid(),{}).get('cpu_ticks')}
    if result['camera'] and result['camera'].get('available'):
        LAST_CAMERA_PID=result['camera']['numeric'].get('pid',LAST_CAMERA_PID)
    result['camera_pid']=LAST_CAMERA_PID
    result['camera_cpu_ticks']=processes.get(LAST_CAMERA_PID,{}).get('cpu_ticks')
    result['sampling_ms']=(time.monotonic()-started)*1000;return result

if __name__=='__main__':
    phase=Path('/home/root/aura-yuki-validation-20261030/native_integration');out=phase/'paired_ab';out.mkdir(exist_ok=True)
    result=snapshot(os.getpid());(out/'telemetry-inspection.json').write_text(json.dumps(result,indent=2));print(json.dumps(result))
