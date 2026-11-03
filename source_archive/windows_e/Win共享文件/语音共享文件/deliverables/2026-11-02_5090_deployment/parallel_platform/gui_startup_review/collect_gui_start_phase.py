"""Read current startup progress, with strict metadata-only log projections."""
import datetime
import hashlib
import http.client
import json
import os
from pathlib import Path
import re
import subprocess
import time

BOOT='903cfade-b93c-48fa-804e-379be1967313'
ROOT=Path('/home/root/aura-board-business-20261030/production-5259eab11e42af13')
STARTUP_SHA='3fd124287463650f48232cb387c78d01399bad7ddcda483db725163298de4591'
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==BOOT
source=(ROOT/'startup/config.json').read_bytes()
assert hashlib.sha256(source).hexdigest()==STARTUP_SHA
config=json.loads(source);runtime=Path(config['runtime'])

def unit():
    props='MainPID,ActiveState,SubState,Job,Result,ExecMainStatus,TimeoutStartUSec,ActiveEnterTimestampMonotonic,InactiveExitTimestampMonotonic,InvocationID'
    p=subprocess.run(['systemctl','show','aura-avatar-ui.service','--property='+props],capture_output=True,text=True,timeout=5)
    assert p.returncode==0
    value=dict(line.split('=',1) for line in p.stdout.splitlines() if '=' in line)
    return {key:value.get(key) for key in props.split(',')}

def processes():
    result={}
    hz=os.sysconf('SC_CLK_TCK')
    for p in Path('/proc').iterdir():
        if not p.name.isdigit():continue
        try:
            fields=(p/'stat').read_text().rsplit(')',1)[1].split()
            cmd=(p/'cmdline').read_bytes();args=cmd.split(b'\0')
            label='other'
            for name in ('launcher.py','board_avatar_pan.py','gstreamer_audio_worker.py',
                         'audio_frontend_host.py','native_entry.py'):
                if any(item.endswith(b'/'+name.encode()) for item in args):label=name;break
            if label=='other' and b'multiprocessing.spawn' in cmd:label='python_multiprocessing_spawn'
            if label=='other' and b'multiprocessing.resource_tracker' in cmd:label='python_multiprocessing_resource_tracker'
            wchan=(p/'wchan').read_text().strip()
            if not re.fullmatch(r'[A-Za-z0-9_]+',wchan):wchan=None
            result[int(p.name)]={'pid':int(p.name),'ppid':int(fields[1]),'state':fields[0],
                'birth_ticks':fields[19],'cpu_seconds':(int(fields[11])+int(fields[12]))/hz,
                'threads':int(fields[17]),'wchan':wchan,'role':label,
                'command_sha256':hashlib.sha256(cmd).hexdigest()}
        except (FileNotFoundError,ProcessLookupError):continue
    return result

def family(allp,roots):
    selected=set(int(p) for p in roots)
    while True:
        more={p for p,value in allp.items() if value['ppid'] in selected}
        if more<=selected:break
        selected|=more
    return [allp[p] for p in sorted(selected) if p in allp]

def log_projection(text):
    frames=[];types=[];events=[]
    public_events={'CHILD_STARTING','CHILD_EXITED','GUI_READY','DISPLAY_READY','READY','FAILED',
        'DISPLAY_RETRAIN_INCOMPLETE','STOP_API_UNAVAILABLE','STOP_DIAGNOSTIC_INCOMPLETE'}
    for line in text.splitlines():
        m=re.match(r'\s*File "([^"]+)", line (\d+), in ([A-Za-z0-9_<>.]+)',line)
        if m and (m[1].startswith('/usr/lib/python') or '/runtime/aura/' in m[1] or '/startup/launcher.py' in m[1]):
            frames.append({'file':m[1],'line':int(m[2]),'function':m[3]})
        m=re.match(r'^([A-Za-z_][A-Za-z0-9_.]*(?:Error|Exception|Warning))(?::|$)',line)
        if m:types.append(m[1])
        try:
            item=json.loads(line)
            if isinstance(item,dict) and item.get('event') in public_events:
                event={'event':item['event']}
                for key in ('returncode','was_ready','display_setup_done','elapsed_seconds','retrained','pid'):
                    if type(item.get(key)) in (bool,int,float):event[key]=item[key]
                if item['event']=='FAILED' and isinstance(item.get('error'),str):
                    error_type=item['error'].split(':',1)[0]
                    if re.fullmatch(r'[A-Za-z_][A-Za-z0-9_.]*',error_type):event['error_type']=error_type
                events.append(event)
        except (ValueError,TypeError):pass
    return {'traceback_count':text.count('Traceback (most recent call last):'),
        'traceback_frames':frames[-32:],'exception_types':types[-12:],'public_events':events[-20:],
        'ready_marker_seen':any(line.startswith('READY ') for line in text.splitlines()),
        'known_public_error_flags':{key:phrase in text for key,phrase in {
            'gui_api_readiness_timeout':'GUI API readiness timed out',
            'display_startup_timeout':'Display startup timed out',
            'readback_boot_rejected':'Readback configuration belongs to another boot',
            'exact_motion_platform_rejected':'Exact board/boot/firmware/VART context required; no MMIO',
            'model_request_deadline':'Model request deadline expired',
            'audio_pipeline_start_failed':'Persistent ALSA start failed',
        }.items()},'log_text_exported':False}

before_unit=unit()
launch_path=runtime/'launch.json';assert not launch_path.is_symlink()
launch=json.loads(launch_path.read_bytes())
assert launch['boot_id']==BOOT and launch['supervisor_pid']==16314 and launch['pid']==16318
roots=(16314,16318)
before=family(processes(),roots);time.sleep(1.2);after=family(processes(),roots)
log_path=Path(launch['log']).resolve(strict=True)
assert log_path.is_relative_to((runtime/'managed-runs').resolve(strict=True))
size=log_path.stat().st_size
with log_path.open('rb') as stream:
    stream.seek(max(0,size-196608));tail=stream.read(196608).decode('utf-8','replace')
stage=log_projection(tail);stage.update(file_bytes=size,tail_bytes_read=min(size,196608))
invocation=before_unit.get('InvocationID','')
journal=None
if re.fullmatch(r'[a-f0-9]{32}',invocation or ''):
    p=subprocess.run(['journalctl','_SYSTEMD_INVOCATION_ID='+invocation,'-n','80','--no-pager','-o','cat'],
        capture_output=True,text=True,timeout=8)
    journal=log_projection(p.stdout) if p.returncode==0 else {'read_succeeded':False,'returncode':p.returncode}
status_files={}
session=Path(launch['session']).resolve(strict=True)
assert session.is_relative_to((runtime/'managed-runs').resolve(strict=True))
for name in ('gui-ready.json','setup.json','ready.json'):
    p=session/name
    entry={'exists':p.exists()}
    if p.is_file() and not p.is_symlink():
        value=json.loads(p.read_bytes())
        if name=='setup.json':
            entry.update({key:value[key] for key in ('physical_panel_verified','startup_output_retrained','startup_retrain_attempted','display_wait_elapsed_seconds') if type(value.get(key)) in (bool,int,float)})
        else:
            entry['same_boot']=value.get('boot_id')==BOOT
            entry['same_supervisor']=value.get('supervisor_pid')==16314
            entry['same_child']=value.get('pid')==16318
        entry['raw_state_exported']=False
    status_files[name]=entry
api={'reachable':False}
c=http.client.HTTPConnection('127.0.0.1',8783,timeout=2)
try:
    c.request('GET','/api/state');r=c.getresponse();body=r.read(2097153)
    if r.status==200 and len(body)<=2097152:
        value=json.loads(body)
        api={'reachable':True,'backend_is_gtk':value.get('backend')=='gtk3-gstreamer',
            'cached_only':value.get('cached_only') is True,
            'sequence':value.get('sequence') if type(value.get('sequence')) is int else None}
except (OSError,ValueError,http.client.HTTPException) as exc:api['error_type']=type(exc).__name__
finally:c.close()
assert hashlib.sha256((ROOT/'startup/config.json').read_bytes()).hexdigest()==STARTUP_SHA
print(json.dumps({'schema':'aura-gui-startup-phase-metadata-1','boot_id':BOOT,
    'board_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'board_mono':time.monotonic(),
    'ready_wait_seconds':config.get('ready_wait_seconds'),'unit_before':before_unit,'unit_after':unit(),
    'process_samples':[before,after],'stage_log':stage,'current_invocation_journal':journal,
    'status_files':status_files,'api':api,'startup_sha256':STARTUP_SHA,
    'board_mutations':False,'commands_sent':False,'full_logs_or_environment_exported':False,
    'database_opened':False,'private_content_or_images_exported':False},sort_keys=True))
