"""Root-only passive scheduler and capture sampling with numeric output.

The local entry is dry by default. Execution reads the existing localhost state
API and /proc. It never opens a device, database, model or process memory.
"""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import time


HERE = Path(__file__).resolve().parent
REPAIR = HERE.parent
BASELINE = REPAIR/'release_v18_newboot_candidate/newboot_evidence/source_mapping.json'

REMOTE_SETUP = r'''
import os
from pathlib import Path

_root = Path(BASELINE['root'])
_boot_path = Path('/proc/sys/kernel/random/boot_id')
_startup_path = _root/'startup/config.json'
_hertz = os.sysconf('SC_CLK_TCK')
_pagesize = os.sysconf('SC_PAGE_SIZE')
_state_codes = set('RSDTtZXIP')
_error_codes = {'', 'none', 'ValueError', 'TypeError', 'RuntimeError', 'TimeoutError',
    'InterruptedError', 'OSError', 'AssertionError', 'ReplyRejected', 'ModelRequestError',
    'PermissionError', 'StaleGeneration', 'ScopeDenied', 'StaleTurn', 'MemoryBusy',
    'MemoryError', 'KeyError', 'AttributeError', 'IndexError', 'BrokenPipeError',
    'ConnectionError', 'OperationalError', 'BufferError', 'FrontendProcessError',
    'pcm_input_queue_overflow', 'pcm_input_truncated_frame', 'pcm_input_read_failed',
    'frontend_auto_capture_failed', 'frontend_worker_read_timeout', 'frontend_worker_write_timeout'}
_reasons = {'', 'DIRECT_SPEECH', 'SPEECH_ACCEPTED', 'AUDIO_WAKE_WORD', 'WAKE_ACCEPTED',
    'CURRENT_TURN_CANCELLED', 'SERVICE_ERROR', 'CAPTURE_ERROR', 'CONVERSATION_SILENCE',
    'SILENCE_TIMEOUT', 'AUDIO_OWNER_CHANGED', 'USER_PAUSED', 'EXPLICIT_USER_PAUSE',
    'SERVICE_NOT_READY', 'BUSINESS_OR_NATIVE_NOT_READY', 'NO_VALID_INITIAL_SPEECH',
    'WAITING_FRESH_FACE', 'VISUAL_UNAVAILABLE', 'LISTENING_PREFERENCE_UNAVAILABLE'}

def _hash_file(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def _check_baseline(full=False):
    if _boot_path.read_text().strip() != BASELINE['boot_id']:
        raise RuntimeError('COLLECTOR_BOOT_CHANGED')
    if _hash_file(_startup_path) != BASELINE['startup_sha256']:
        raise RuntimeError('COLLECTOR_STARTUP_CHANGED')
    if full:
        for relative, fingerprint in BASELINE['component_pins'].items():
            path = _root/'runtime/aura'/relative
            if path.resolve(strict=True) != path or _hash_file(path) != fingerprint:
                raise RuntimeError('COLLECTOR_SOURCE_CHANGED')

def _stat(path):
    raw = path.read_text()
    fields = raw.rsplit(')', 1)[1].split()
    if len(fields) < 39:
        raise ValueError('COLLECTOR_STAT_SCHEMA')
    return dict(state=fields[0] if fields[0] in _state_codes else 'other',
        ppid=int(fields[1]), user_ticks=int(fields[11]), system_ticks=int(fields[12]),
        priority=int(fields[15]), nice=int(fields[16]), num_threads=int(fields[17]),
        birth_ticks=int(fields[19]), virtual_bytes=int(fields[20]),
        rss_pages=int(fields[21]), last_cpu=int(fields[36]))

def _error(value):
    if not isinstance(value, str):
        return dict(present=bool(value), code='other' if value else '', length=None)
    prefix = value.split(':', 1)[0]
    key = value if value in _error_codes else prefix if prefix in _error_codes else 'other'
    return dict(present=bool(value) and value != 'none', code=key, length=len(value))

def _numbers(value, names):
    if not isinstance(value, dict):
        return {}
    return {key:value[key] for key in names if type(value.get(key)) in (int,float)
            and math.isfinite(value[key]) and 0 <= value[key] <= 9007199254740991}

def _wait_class(path):
    try:
        value = path.read_text().strip()
    except OSError:
        return 'unavailable'
    if 'futex' in value:
        return 'futex'
    if 'pipe' in value:
        return 'pipe'
    if 'epoll' in value or 'poll_' in value:
        return 'poll'
    if 'sleep' in value:
        return 'sleep'
    if 'sock' in value or 'unix_stream' in value:
        return 'socket'
    return 'running_or_hidden' if value == '0' else 'other'

def _process(pid, expected=None, parent_pid=None):
    path = Path('/proc')/str(pid)
    before = _stat(path/'stat')
    if expected is not None:
        if before['birth_ticks'] != expected['birth_ticks']:
            raise RuntimeError('COLLECTOR_PROCESS_REUSED')
        fingerprint = expected.get('command_sha256')
        if fingerprint and _hash_file(path/'cmdline') != fingerprint:
            raise RuntimeError('COLLECTOR_OWNER_CHANGED')
    if parent_pid is not None and before['ppid'] != parent_pid:
        return dict(pid=pid, eligible=False, reason='parent_mismatch')
    threads = []
    task_paths = sorted((p for p in (path/'task').iterdir() if p.name.isdigit()), key=lambda p:int(p.name))
    for task in task_paths[:256]:
        try:
            value = _stat(task/'stat')
            row = dict(tid=int(task.name), **value)
            try:
                scheduler = [int(x) for x in (task/'schedstat').read_text().split()]
                if len(scheduler) == 3:
                    row['scheduler'] = dict(runtime_ns=scheduler[0], runqueue_wait_ns=scheduler[1], timeslices=scheduler[2])
            except (OSError, ValueError):
                row['scheduler_unavailable'] = True
            row['wait_class'] = _wait_class(task/'wchan')
            switches = {}
            for line in (task/'status').read_text().splitlines():
                key, _, value = line.partition(':')
                if key in ('voluntary_ctxt_switches', 'nonvoluntary_ctxt_switches'):
                    switches[key] = int(value.strip())
            row['context_switches'] = switches
            threads.append(row)
        except (FileNotFoundError, ProcessLookupError):
            continue
    after = _stat(path/'stat')
    if after['birth_ticks'] != before['birth_ticks']:
        raise RuntimeError('COLLECTOR_PROCESS_REUSED_DURING_SAMPLE')
    return dict(pid=pid, eligible=True, process=after, threads=threads,
                threads_truncated=len(task_paths)>256)

def _system_cpu():
    result = {}
    for line in Path('/proc/stat').read_text().splitlines():
        parts = line.split()
        if parts and parts[0] == 'cpu':
            result['ticks'] = [int(x) for x in parts[1:11]]
        elif parts and parts[0] in ('procs_running', 'procs_blocked', 'ctxt'):
            result[parts[0]] = int(parts[1])
    try:
        result['sched_schedstats_enabled'] = Path('/proc/sys/kernel/sched_schedstats').read_text().strip() == '1'
    except OSError:
        result['sched_schedstats_enabled'] = None
    return result

def _scheduler_sample(raw_state, safe_out):
    _check_baseline()
    processes = {}
    for name in ('supervisor','gtk','camera'):
        expected = BASELINE[name]
        processes[name] = _process(expected['pid'], expected=expected)
    frontend = raw_state.get('audio_frontend', {}).get('current', {})
    frontend = frontend if isinstance(frontend, dict) else {}
    worker_pid = frontend.get('worker_pid')
    if type(worker_pid) is int and worker_pid > 1:
        try:
            processes['frontend'] = _process(worker_pid, parent_pid=BASELINE['gtk']['pid'])
        except (FileNotFoundError, ProcessLookupError):
            processes['frontend'] = dict(pid=worker_pid, eligible=False, reason='exited')
    microphone_pid = frontend.get('microphone_pid')
    if type(microphone_pid) is int and microphone_pid > 1 and processes.get('frontend', {}).get('eligible'):
        try:
            processes['microphone'] = _process(microphone_pid, parent_pid=worker_pid)
        except (FileNotFoundError, ProcessLookupError):
            processes['microphone'] = dict(pid=microphone_pid, eligible=False, reason='exited')
    renderer = raw_state.get('avatar_renderer', {})
    renderer = renderer if isinstance(renderer, dict) else {}
    results = renderer.get('command_results', [])
    results = results if isinstance(results, list) else []
    commands = [item for item in results[-16:] if isinstance(item, dict)]
    ids = [item.get('command_id') for item in commands if isinstance(item.get('command_id'), str)]
    errors = [_error(item.get('error', '')) for item in commands if item.get('ok') is not True]
    handsfree = raw_state.get('handsfree_dialogue', {})
    handsfree = handsfree if isinstance(handsfree, dict) else {}
    capture = raw_state.get('safe_capture_diagnostics', {})
    capture = capture if isinstance(capture, dict) else {}
    failure = frontend.get('last_capture_failure', {})
    failure = failure if isinstance(failure, dict) else {}
    fault = renderer.get('worker_faults', {})
    fault = fault if isinstance(fault, dict) else {}
    last = fault.get('last', {})
    last = last if isinstance(last, dict) else {}
    return dict(observed_mono=time.monotonic(), startup_sha256=BASELINE['startup_sha256'],
        phase=stage(raw_state.get('phase')), playing=raw_state.get('playing') is True,
        processes=processes, system_cpu=_system_cpu(),
        native=_numbers(raw_state.get('avatar_display'), ('frames','native_call_ms','gtk_callback_ms','age_ms','stale_frames')),
        ui_callback=_numbers(raw_state.get('ui_callback_previous'), ('wall_ms','thread_cpu_ms','publish_ms','sequence','completed_mono')),
        capture_counts=_numbers(capture.get('counters'), ('armed','speech_starts','submitted','entry_rejected','visual_stops')),
        frontend=_numbers(frontend, ('worker_pid','worker_generation','microphone_pid','capture_failures','frames',
            'endpoint_feed_wall_total_ms','endpoint_feed_cpu_total_ms','consumer_gap_total_ms','consumer_gap_count')),
        capture_failure=dict(error=_error(failure.get('error_code','')),
            queue=_numbers(failure.get('input_queue'), ('peak_frames','frames_read','frames_delivered','queue_max_ms'))),
        monitor=dict(enabled=handsfree.get('enabled') is True, state=stage(handsfree.get('state')),
            conversation_entered=handsfree.get('conversation_entered') is True,
            reason=handsfree.get('reason') if handsfree.get('reason') in _reasons else 'other',
            microphone_open=handsfree.get('microphone_open') is True),
        errors=dict(top=_error(raw_state.get('error','')), monitor=_error(handsfree.get('error',''))),
        commands=dict(retained=len(commands), successful=sum(item.get('ok') is True for item in commands),
            failed=len(errors), errors=errors, unknown_error_count=sum(item['code']=='other' for item in errors),
            identity_digest=hashlib.sha256(json.dumps(ids).encode()).hexdigest()),
        worker_faults=dict(available=bool(fault), count=fault.get('count') if type(fault.get('count')) is int else None,
            last_error=_error(last.get('error_class','')), metadata=_numbers(last, ('observed_mono','sequence'))),
        audio_output=_numbers(raw_state.get('audio_output'), ('underrun_packets','turn_underrun_packets','max_poll_gap_ms')))

_check_baseline(full=True)
'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--execute-root-only', action='store_true')
    parser.add_argument('--samples', type=int, choices=range(2,62), default=31)
    parser.add_argument('--baseline', type=Path, default=BASELINE)
    args = parser.parse_args()
    baseline = json.loads(args.baseline.read_text(encoding='utf-8-sig'))
    probe_path = REPAIR/'probe.py'
    spec = importlib.util.spec_from_file_location('existing_root_metadata_probe', probe_path)
    probe = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(probe)
    marker = 'print(json.dumps(out))'
    if probe.REMOTE.count(marker) != 1:
        raise ValueError('Existing root probe changed')
    source = probe.REMOTE.replace(marker, '')
    # Setup uses only these imports from the existing probe before its first API call.
    script = ('import hashlib,json,math,time\nBASELINE='+repr(baseline)+'\n'+REMOTE_SETUP
        +'\nSOURCE='+repr(source)+'\nSAMPLES='+str(args.samples)+'''\n
print(json.dumps(dict(kind='header', clock_ticks_per_second=_hertz, page_bytes=_pagesize,
    source_components_verified=len(BASELINE['component_pins']), raw_cmdline_or_thread_names_exported=False)))
for _index in range(SAMPLES):
    _began = time.monotonic()
    _cpu_began = time.process_time()
    exec(SOURCE)
    _observed = _scheduler_sample(state, out)
    _observed['collector_wall_ms'] = (time.monotonic()-_began)*1000
    _observed['collector_cpu_ms'] = (time.process_time()-_cpu_began)*1000
    print(json.dumps(_observed), flush=True)
    if _index+1 < SAMPLES:
        time.sleep(max(0., 1.-(time.monotonic()-_began)))
_check_baseline()
''')
    compile(script, '<passive_scheduler_collector>', 'exec')
    if not args.execute_root_only:
        print(json.dumps(dict(status='DRY_READY', samples=args.samples,
            startup_sha256=baseline['startup_sha256'], remote_script_sha256=hashlib.sha256(script.encode()).hexdigest())))
        return
    rows = [json.loads(line) for line in probe.ssh('python3 -B -', script, timeout=args.samples*3+30).splitlines() if line.strip()]
    if len(rows) != args.samples+1 or rows[0].get('kind') != 'header':
        raise ValueError('Incomplete scheduler sample window')
    output = HERE/('scheduler_'+str(time.time_ns())+'.json')
    with output.open('x', encoding='utf-8') as stream:
        json.dump(dict(schema='aura.passive-runtime-scheduler.v1', header=rows[0], samples=rows[1:],
            collector_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            baseline_sha256=hashlib.sha256(args.baseline.read_bytes()).hexdigest(),
            root_probe_sha256=hashlib.sha256(probe_path.read_bytes()).hexdigest(),
            raw_state_saved=False, production_changed=False), stream, indent=2)
        stream.write('\n')
    print(json.dumps(dict(status='COLLECTED', output=str(output), samples=len(rows)-1)))


if __name__ == '__main__':
    main()
