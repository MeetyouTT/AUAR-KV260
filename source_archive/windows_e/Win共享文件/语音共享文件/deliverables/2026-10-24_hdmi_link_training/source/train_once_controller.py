"""Explicit one-shot DP training candidate; default only performs preflight.

No boot hook, model instance, modeset, splitter command or firmware write.
An unreturned sysfs operation keeps its process/module; never force-unload it.
"""
import argparse
import ctypes as C
import ctypes.util
import gzip
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import urllib.request

MODULE_NAME = 'aura_dp_retrain_candidate'
MODULE_SHA = '2e5bd549c33d23a2585710058d73b1a75f7e073b40a6884d426550735196a01d'
MODULE_FILE = Path('/home/root/aura-display-sequence-20261024/module-diagnostic/3887f8fe88724c74/aura_dp_retrain_candidate.ko')
CONFIG_SHA = 'abded1ea95a5208287e66ef4a4f6fc7f0591771a8a3e3bd80737e8b557df96a8'
PARAMS = Path('/sys/module') / MODULE_NAME / 'parameters'
SOURCE = Path(__file__).resolve()
TOKEN = hashlib.sha256(SOURCE.read_bytes()).hexdigest()[:16]
BASE = Path('/home/root/aura-display-sequence-20261024/one-shot')


def boot():
    return Path('/proc/sys/kernel/random/boot_id').read_text().strip()


def atomic(path, value):
    path = Path(path);temporary = path.with_suffix('.tmp')
    with temporary.open('w') as out:
        json.dump(value, out, indent=2);out.write('\n');out.flush();os.fsync(out.fileno())
    os.replace(temporary, path)


def run(args, timeout=8):
    return subprocess.check_output(args, text=True, stderr=subprocess.PIPE, timeout=timeout)


def camera():
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    with opener.open('http://127.0.0.1:8790/health', timeout=3) as stream:
        raw = json.load(stream)
    schedule = raw['dpu_schedule']
    return dict(pid=raw['pid'], frames=raw['detected_frames'],
        native_critical=schedule.get('native_critical'), abi=schedule.get('native_abi'),
        owner_fenced=schedule['owner_fenced'], primary_overruns=schedule['primary_period_overruns'],
        optional_overruns={kind:job['overruns'] for kind,job in schedule['optional'].items()},
        worker_alive=raw['identity']['face_targets']['worker_alive'],
        camera_error=bool(raw.get('camera_error') or raw.get('detector_error')))


def cached_display():
    p = Path('/sys/class/drm/card0-DP-1')
    state = Path('/sys/kernel/debug/dri/0/state').read_text()
    return dict(connector={key:(p/key).read_text().strip() for key in ('status','enabled','dpms')},
        scanout=[s.strip() for s in state.splitlines() if any(key in s for key in
            ('format=','size=','pitch=','crtc-pos=','mode:')) or s.strip().startswith(('enable=','active='))])


def validate_context(expected_boot, expected_pid, actual_boot, health, display):
    if actual_boot != expected_boot:
        raise ValueError('Kernel boot changed')
    if health['pid'] != expected_pid:
        raise ValueError('Camera process changed')
    if health['native_critical'] is not True or health['abi'] != 2:
        raise ValueError('Unexpected model execution backend')
    if health['owner_fenced'] or health['camera_error'] or not health['worker_alive']:
        raise ValueError('Camera execution unavailable')
    connector = display['connector']
    if connector != dict(status='connected', enabled='enabled', dpms='On'):
        raise ValueError('Display is inactive; do not wake/modeset and mix experiments')


def can_unload(load_confirmed, trigger_started, trigger_returned):
    return load_confirmed and (not trigger_started or trigger_returned)


def smoke_passed(report):
    after=report.get('after_camera',{})
    return bool('failure' not in report and report.get('driver_call_returned')
        and report.get('post_training_vblank_returned') and report.get('module_removed')
        and report.get('training_function_entries')==1 and report.get('encoder_enable_entries')==0
        and report.get('encoder_disable_entries')==0 and report.get('same_camera_pid')
        and report.get('cached_display_unchanged') and not any(report.get('new_optional_overruns',{}).values())
        and report.get('new_primary_overruns')==0 and report.get('new_camera_frames',0)>0
        and not after.get('owner_fenced',True) and not after.get('camera_error',True)
        and after.get('worker_alive') is True)


def kernel_check():
    assert os.uname().release == '5.15.36-xilinx-v2022.2'
    raw = gzip.decompress(Path('/proc/config.gz').read_bytes()).decode()
    values = {row.split('=',1)[0]:row.split('=',1)[1] for row in raw.splitlines()
        if row.startswith('CONFIG_') and not row.startswith('CONFIG_CC_VERSION_TEXT=')}
    assert hashlib.sha256(json.dumps(values,sort_keys=True,separators=(',',':')).encode()).hexdigest() == CONFIG_SHA
    assert hashlib.sha256(MODULE_FILE.read_bytes()).hexdigest() == MODULE_SHA
    assert not PARAMS.parent.exists(), 'Refuse taking ownership of an existing module'


class Request(C.Structure):
    _fields_=[('type',C.c_uint),('sequence',C.c_uint),('signal',C.c_ulong)]
class Reply(C.Structure):
    _fields_=[('type',C.c_uint),('sequence',C.c_uint),('sec',C.c_long),('usec',C.c_long)]
class Vblank(C.Union):
    _fields_=[('request',Request),('reply',Reply)]


def readonly_query():
    assert C.sizeof(Vblank) == 24
    drm = C.CDLL(ctypes.util.find_library('drm'), use_errno=True)
    drm.drmModeGetResources.argtypes=[C.c_int];drm.drmModeGetResources.restype=C.c_void_p
    drm.drmModeFreeResources.argtypes=[C.c_void_p];drm.drmModeFreeResources.restype=None
    drm.drmWaitVBlank.argtypes=[C.c_int,C.POINTER(Vblank)];drm.drmWaitVBlank.restype=C.c_int
    fd = os.open('/dev/dri/card0', os.O_RDONLY | os.O_CLOEXEC)
    try:
        resource = drm.drmModeGetResources(fd)
        if not resource:raise OSError(C.get_errno(),'GETRESOURCES failed')
        drm.drmModeFreeResources(resource)
        wait=Vblank();wait.request.type=1;wait.request.sequence=1
        if drm.drmWaitVBlank(fd,C.byref(wait)):raise OSError(C.get_errno(),'VBLANK wait failed')
    finally:os.close(fd)


def checked_root(text):
    root = Path(text)
    assert root.parent == BASE and root.name == boot() + '-' + TOKEN
    assert root.resolve() == root and not root.is_symlink()
    meta = json.loads((root/'meta.json').read_text())
    assert meta['source_sha256'] == hashlib.sha256(SOURCE.read_bytes()).hexdigest()
    assert meta['module_sha256'] == MODULE_SHA and meta['expected_boot'] == boot()
    return root, meta


def trigger_child(text):
    root,meta = checked_root(text)
    result = dict(started_mono_ns=time.monotonic_ns(),returned=False)
    try:
        status=dict(item.split('=',1) for item in (PARAMS/'status').read_text().split())
        assert status['ready']=='1' and status['enable_action']=='1' and status['triggered']=='0'
        validate_context(meta['expected_boot'],meta['camera_pid'],boot(),camera(),cached_display())
        (PARAMS/'trigger').write_text('1')
        result.update(returned=True,finished_mono_ns=time.monotonic_ns(),module_status=(PARAMS/'status').read_text().strip())
    except Exception as exc:
        result.update(returned=True,error_type=type(exc).__name__,error=str(exc))
    atomic(root/'trigger-result.json',result)
    return 1 if 'error' in result else 0


def worker(text):
    root,meta = checked_root(text)
    report=dict(scope='ONE_EXPLICIT_EXISTING_DRIVER_TRAIN_ONLY',boot=boot(),
        visual_verified=False, internal_training_success_measured=False,
        model_instances_created=0,mode_setting_commands=0,firmware_writes=0,
        module_removed=False,completion_unconfirmed=False,accepted_trigger_count=0)
    load=None;child=None;loaded=False;trace=None
    try:
        kernel_check()
        report['before_camera']=camera();report['before_display']=cached_display()
        validate_context(meta['expected_boot'],meta['camera_pid'],boot(),report['before_camera'],report['before_display'])
        atomic(root/'progress.json',dict(phase='LOADING_DIAGNOSTIC_INTERFACES',report=report))
        load=subprocess.Popen(['insmod',str(MODULE_FILE),'enable_action=1','capture_timeout_ms=5000'],
            stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
        for unused in range(12):
            if load.poll() is not None:break
            readonly_query();time.sleep(.1)
        stdout,stderr=load.communicate(timeout=15)
        report.update(load_exit=load.returncode,load_error=stderr[-800:])
        assert load.returncode==0,'Module not ready'
        loaded=True
        candidate_trace=Path('/sys/kernel/tracing/instances')/('aura_once_'+TOKEN+'_'+boot()[:8])
        assert not candidate_trace.exists();candidate_trace.mkdir();trace=candidate_trace
        (trace/'tracing_on').write_text('0');(trace/'buffer_size_kb').write_text('64')
        (trace/'trace_clock').write_text('mono')
        (trace/'set_ftrace_filter').write_text('zynqmp_dp_train_loop\nzynqmp_dp_encoder_enable\nzynqmp_dp_encoder_disable\n')
        (trace/'current_tracer').write_text('function');(trace/'tracing_on').write_text('1')
        atomic(root/'progress.json',dict(phase='ONE_TRIGGER_BEGIN',report=report))
        # This worker is separately owned. A timed-out kernel callback is not
        # killed or force-unloaded, even if the parent returns a blocked result.
        child=subprocess.Popen(['/usr/bin/python3','-B',str(SOURCE),'--trigger-root',str(root)],
            stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        try:child.wait(timeout=20)
        except subprocess.TimeoutExpired:
            report.update(completion_unconfirmed=True,retained_trigger_pid=child.pid)
            raise RuntimeError('Trigger still running; process and module retained')
        report['trigger_child_exit']=child.returncode
        result=json.loads((root/'trigger-result.json').read_text())
        report['trigger_result']=result
        assert child.returncode==0 and result['returned'] and 'error' not in result
        fields=dict(item.split('=',1) for item in result['module_status'].split())
        assert fields['triggered']=='1' and fields['action_returned']=='1' and fields['action_error']=='0'
        report.update(accepted_trigger_count=1,driver_call_returned=True)
        readonly_query()
        report['post_training_vblank_returned']=True
        time.sleep(.5)
    except Exception as exc:
        report.update(failure_type=type(exc).__name__,failure=str(exc))
    finally:
        if load is not None and load.poll() is None:
            report.update(completion_unconfirmed=True,retained_loader_pid=load.pid)
        if trace is not None and trace.exists():
            (trace/'tracing_on').write_text('0')
            raw=(trace/'trace').read_text();(root/'function-trace.private.txt').write_text(raw)
            report['training_function_entries']=sum('zynqmp_dp_train_loop <-' in row for row in raw.splitlines())
            report['encoder_enable_entries']=sum('zynqmp_dp_encoder_enable <-' in row for row in raw.splitlines())
            report['encoder_disable_entries']=sum('zynqmp_dp_encoder_disable <-' in row for row in raw.splitlines())
            (trace/'current_tracer').write_text('nop');(trace/'set_ftrace_filter').write_text('');trace.rmdir()
        if can_unload(loaded,child is not None,child is not None and child.poll() is not None):
            try:run(['rmmod',MODULE_NAME],10)
            except Exception as exc:report['unload_error']=type(exc).__name__
        report['module_removed']=not PARAMS.parent.exists()
        try:
            report['after_camera']=camera();report['after_display']=cached_display()
            report['same_camera_pid']=report.get('before_camera',{}).get('pid')==report['after_camera']['pid']
            report['cached_display_unchanged']=report.get('before_display')==report['after_display']
            before=report.get('before_camera',{});after=report['after_camera']
            report['new_optional_overruns']={kind:value-before.get('optional_overruns',{}).get(kind,value)
                for kind,value in after['optional_overruns'].items()}
            report['new_primary_overruns']=after['primary_overruns']-before.get('primary_overruns',after['primary_overruns'])
            report['new_camera_frames']=after['frames']-before.get('frames',after['frames'])
        except Exception as exc:report['postcheck_error']=type(exc).__name__
        # Returning from the void native function is not proof of link or
        # picture correctness. Keep those fields false until independently tested.
        report['phase']='RETURNED' if report.get('driver_call_returned') else 'NOT_VERIFIED'
        report['driver_smoke_passed']=smoke_passed(report)
        atomic(root/'result.json',report);atomic(root/'progress.json',report)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--launch-once',action='store_true')
    parser.add_argument('--boot');parser.add_argument('--camera-pid',type=int)
    parser.add_argument('--worker-root');parser.add_argument('--trigger-root')
    args=parser.parse_args()
    if args.trigger_root:return trigger_child(args.trigger_root)
    if args.worker_root:worker(args.worker_root);return 0
    kernel_check();health=camera();display=cached_display()
    if not args.launch_once:
        print(json.dumps(dict(scope='PREFLIGHT_ONLY_NO_LOAD_NO_RETRAIN',boot=boot(),camera=health,
            display=display,module_sha256=MODULE_SHA,source_sha256=hashlib.sha256(SOURCE.read_bytes()).hexdigest())))
        return 0
    validate_context(args.boot,args.camera_pid,boot(),health,display)
    root=BASE/(boot()+'-'+TOKEN);root.mkdir(parents=True,exist_ok=False,mode=0o700)
    meta=dict(expected_boot=args.boot,camera_pid=args.camera_pid,module_sha256=MODULE_SHA,
        source_sha256=hashlib.sha256(SOURCE.read_bytes()).hexdigest(),initial_camera=health,initial_display=display)
    atomic(root/'meta.json',meta)
    unit='aura-one-train-'+TOKEN+'-'+boot()[:8]
    subprocess.run(['systemd-run','--quiet','--no-block','--unit='+unit,'--property=Type=oneshot',
        '--property=TimeoutStartSec=infinity','--property=TimeoutStopSec=infinity',
        '--property=KillMode=process','--property=SendSIGKILL=no','--property=Restart=no',
        '/usr/bin/python3','-B',str(SOURCE),'--worker-root',str(root)],check=True)
    print(json.dumps(dict(phase='LAUNCHED_EXPLICIT_ONE_SHOT',unit=unit,root=str(root))))
    return 0


if __name__=='__main__':
    sys.exit(main())
