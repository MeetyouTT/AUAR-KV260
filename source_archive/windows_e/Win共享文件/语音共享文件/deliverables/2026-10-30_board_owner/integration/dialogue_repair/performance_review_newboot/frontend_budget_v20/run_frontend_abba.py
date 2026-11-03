"""Root-only sequential public frontend screen, dry by default."""
import argparse
import json
import os
from pathlib import Path
import platform
import signal
import subprocess
import sys
import time

import frontend_v20_common as current
from compare_frontend_abba import compare


ORDER = (('A1', 'baseline_1'), ('B1', 'dual_nospin'),
         ('B2', 'dual_nospin'), ('A2', 'baseline_1'))
STAGE_PARENT = Path('/home/root/aura-public-frontend-v20-20261031')


def worker_command(slot, mode, package_sha):
    command = [sys.executable, '-B', str(current.HERE / 'public_frontend_budget.py'),
               '--execute-root-only', '--package-sha256', package_sha, '--slot', slot, '--mode', mode]
    values = dict(source_mapping=current.HERE / 'source_mapping.v20.json', code_root=current.ROOT / 'runtime/aura',
        pipeline_helper=current.HERE / 'allocation_public_probe.py', pump_helper=current.HERE / 'board_audio_runtime_probe.py',
        wav=current.WAV, frontend_models=current.FRONTEND_MODELS, fft_deps=current.FFT_DEPS, asr_deps=current.ASR_DEPS)
    for name, path in values.items():
        command += ['--' + name.replace('_', '-'), str(path)]
    return command


def own_child(process, identity):
    current.need(current.process_identity(process.pid) == identity
                 and current.process_parent(process.pid) == os.getpid()
                 and os.getpgid(process.pid) == process.pid and process.pid != os.getpgrp(),
                 'OWNED_PROCESS_PROOF_LOST')


def run_child(slot, mode, package_sha, batch_deadline):
    command = worker_command(slot, mode, package_sha)
    started = time.monotonic()
    deadline = min(batch_deadline, started + 90.)
    current.need(deadline - started > 10., 'BATCH_DEADLINE')
    process = subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
        stderr=subprocess.PIPE, text=True, encoding='utf-8', start_new_session=True,
        env=dict(os.environ, OMP_NUM_THREADS='1', OPENBLAS_NUM_THREADS='1', MKL_NUM_THREADS='1',
                 PYTHONNOUSERSITE='1', PYTHONDONTWRITEBYTECODE='1'))
    identity = None
    value = None
    try:
        identity = current.process_identity(process.pid)
        expected_command = current.sha(b'\0'.join(part.encode() for part in command) + b'\0')
        current.need(identity['command_sha256'] == expected_command, 'OWNED_CHILD_COMMAND_CHANGED')
        own_child(process, identity)
        # Reserve eight seconds inside the 90-second bound for owned cleanup.
        stdout, stderr = process.communicate(timeout=max(.1, deadline - time.monotonic() - 8.))
        current.need(len(stdout) <= 1048576, 'PUBLIC_RESULT_TOO_LARGE')
        value = json.loads(stdout)
        current.need(value.get('slot') == slot and value.get('mode') == mode
                     and value.get('startup_sha256') == current.STARTUP_SHA
                     and value.get('source_mapping_sha256') == current.MAPPING_SHA
                     and value.get('source_components_verified') == 380, 'PUBLIC_RESULT_OWNER_CHANGED')
        current.need(value.get('microphone_opened') is False and value.get('audio_played') is False
                     and value.get('asr_executed') is False and value.get('production_database_opened') is False
                     and value.get('production_source_modified') is False, 'PUBLIC_RESULT_SCOPE_CHANGED')
        value.update(owned_child=identity, child_wall_seconds=time.monotonic() - started,
                     external_deadline_seconds=90., native_stderr_characters=len(stderr))
        if process.returncode != 0 or value.get('status') != 'PASS_PUBLIC_SLOT':
            value['status'] = 'FAILED'
        return value
    finally:
        if process.poll() is None:
            if identity is None:
                identity = current.process_identity(process.pid)
            own_child(process, identity)
            os.killpg(process.pid, signal.SIGTERM)
            try:
                process.communicate(timeout=min(3., max(.1, deadline - time.monotonic())))
            except subprocess.TimeoutExpired:
                own_child(process, identity)
                os.killpg(process.pid, signal.SIGKILL)
                process.communicate(timeout=min(5., max(.1, deadline - time.monotonic())))
        try:
            os.killpg(process.pid, 0)
        except ProcessLookupError:
            pass
        else:
            raise current.Refused('OWNED_PROCESS_GROUP_REMAINS')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--package-sha256', required=True)
    parser.add_argument('--execute-root-only', action='store_true')
    args = parser.parse_args()
    mapping = current.package(args.package_sha256)
    if not args.execute_root_only:
        return dict(status='DRY_V20_PUBLIC_PACKAGE_VALIDATED', order=[slot for slot, _ in ORDER],
                    components=380, startup_sha256=current.STARTUP_SHA, models_loaded=False, device_access=False)
    current.need(platform.system() == 'Linux' and platform.machine().lower() in ('aarch64', 'arm64'),
                 'ARM_LINUX_REQUIRED')
    current.need(current.HERE.parent == STAGE_PARENT and current.HERE.name == args.package_sha256[:16],
                 'OWNED_PROBE_STAGE_REQUIRED')
    current.need(os.getpriority(os.PRIO_PROCESS, 0) == 0 and len(os.sched_getaffinity(0)) == 4,
                 'ORIGINAL_RUNNER_PRIORITY_AND_AFFINITY_REQUIRED')
    import fcntl
    lock_fd = os.open(str(current.HERE / 'owned-probe.lock'), os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
    with os.fdopen(lock_fd, 'a+b') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        initial = current.guard(mapping, full=True)
        deadline = time.monotonic() + 420.
        rows = []
        try:
            for slot, mode in ORDER:
                before = current.guard(mapping, full=False)
                value = run_child(slot, mode, args.package_sha256, deadline)
                after = current.guard(mapping, full=False)
                value['parent_before'], value['parent_after'] = before, after
                if (before['capture_stats'] != after['capture_stats']
                        or before['capture_stats'] != initial['capture_stats']):
                    value.update(status='FAILED', error_code='capture_activity_changed')
                rows.append(value)
                if value['status'] != 'PASS_PUBLIC_SLOT':
                    break
            final = current.guard(mapping, full=True)
            return dict(status='PUBLIC_FRONTEND_ABBA_COMPLETE' if len(rows) == 4
                and all(row['status'] == 'PASS_PUBLIC_SLOT' for row in rows) else 'PUBLIC_FRONTEND_ABBA_STOPPED',
                schema='aura.public-frontend-abba-v20.v1', slots=rows, comparison=compare(rows),
                before=initial, after=final, package_sha256=args.package_sha256,
                source_mapping_sha256=current.MAPPING_SHA, startup_sha256=current.STARTUP_SHA,
                batch_deadline_seconds=420, production_modified=False, microphone_opened=False, audio_played=False)
        except Exception as exc:
            return dict(status='PUBLIC_FRONTEND_ABBA_STOPPED', slots=rows,
                error_code=str(exc) if isinstance(exc, current.Refused) else type(exc).__name__
                if type(exc).__name__ in ('TimeoutExpired', 'TimeoutError', 'ValueError', 'OSError', 'RuntimeError') else 'OtherError',
                package_sha256=args.package_sha256, production_modified=False)


if __name__ == '__main__':
    try:
        result = main()
    except Exception as exc:
        result = dict(status='REFUSED', error_code=str(exc) if isinstance(exc, current.Refused)
                      else type(exc).__name__ if type(exc).__name__ in ('ValueError', 'OSError', 'RuntimeError') else 'OtherError')
    print(json.dumps(result, allow_nan=False))
    raise SystemExit(0 if result['status'] in ('DRY_V20_PUBLIC_PACKAGE_VALIDATED', 'PUBLIC_FRONTEND_ABBA_COMPLETE') else 2)
