"""Parent-run Ubuntu host audit only. Never opens UART or contacts the board.

No raw argv/env, credential, model or business-store content is exported.
CanPowerOff is a read-only logind permission query, never a shutdown request.
"""
import ast
import datetime
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import socket
import subprocess
import sys

ROOT = Path('/home/ghmd/Win共享文件/语音共享文件')
TRANSPORT = Path('/home/ghmd/kv260-dfx-state-boardtest-20261004/scripts/uart_phase.py')


def read_command(args):
    try:
        result = subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=4, text=True)
        return dict(exit_code=result.returncode, stdout=result.stdout[:1500], stderr=result.stderr[:500])
    except (OSError, subprocess.TimeoutExpired) as exc:
        return dict(error=type(exc).__name__)


def main():
    port = None
    try:
        for item in ast.parse(TRANSPORT.read_text()).body:
            if isinstance(item, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'PORT' for t in item.targets):
                port = ast.literal_eval(item.value)
    except (OSError, ValueError, SyntaxError):
        pass
    resolved = os.path.realpath(port) if port else None
    paths = {}
    for relative in ('', 'AGENTS.md', 'aura/board/runtime/audio/board_dialogue_jobs.py',
                     'aura/board/runtime/board_dialogue.py', 'aura/board/runtime/board_dialogue_client.py',
                     'deliverables/2026-10-30_board_owner/ubuntu/jobs_adapter_handoff.json',
                     'deliverables/2026-10-30_board_owner/ubuntu/evidence',
                     'deliverables/2026-10-30_board_owner/integration'):
        path = ROOT / relative
        value = dict(exists=path.exists(), is_dir=path.is_dir(), readable=os.access(str(path), os.R_OK),
                     writable_access_check_only=os.access(str(path), os.W_OK))
        if path.is_file() and path.stat().st_size < 150000:
            value['sha256'] = hashlib.sha256(path.read_bytes()).hexdigest()
        paths[relative or '.'] = value
    scripts = {'run_board_check.py', 'run_uart.py', 'uart_phase.py', 'serve_candidate_assets.py',
               'board_asr_probe.py', 'board_stage_asr.py', 'board_dependency_probe.py',
               'board_candidate_smoke.py', 'board_frontend_probe.py', 'board_frontend_profile.py',
               'board_gtcrn_fft_probe.py', 'gtcrn_fft_windows_probe.py', 'frontend_windows_probe.py',
               'board_semantic_memory_probe.py', 'model_probe_server.py', 'board_clock_probe.py'}
    patterns = ('2026-10-30_board_owner', 'aura-board-owner-candidate-20261030', 'board_asr',
                'board_gtcrn', 'gtcrn_fft', 'board_speaker', 'ecapa', 'speaker-c695',
                'timeline_clock', 'clock_probe', 'uart_phase', 'run_uart', 'run_board_check')
    matches, holders = [], []
    unreadable_cmdline = unreadable_fds = 0
    for proc in Path('/proc').iterdir():
        if not proc.name.isdigit() or int(proc.name) == os.getpid():
            continue
        try:
            argv = (proc / 'cmdline').read_bytes().decode('utf-8', 'replace').rstrip('\0').split('\0')
            fields = (proc / 'stat').read_text().rsplit(') ', 1)[1].split()
            comm = (proc / 'comm').read_text().strip()
        except (OSError, ValueError):
            unreadable_cmdline += 1
            continue
        names = [Path(a).name for a in argv[1:4] if a.endswith('.py')]
        labels = set()
        for value in argv:
            if not value.startswith(('-c', 'import ', 'from ')):
                labels.update(key for key in patterns if key in value)
        if any(name in scripts for name in names):
            labels.add('reviewed_script_name')
        if 'pytest' in argv or any(Path(a).name == 'pytest' for a in argv[:2]):
            labels.add('pytest')
        if labels:
            matches.append(dict(pid=int(proc.name), ppid=int(fields[1]), comm=comm,
                                script_basenames=names, labels=sorted(labels), start_ticks=int(fields[19]),
                                is_inline_python='-c' in argv, raw_argv_exported=False,
                                classification='candidate_or_audit_match_requires_owner_review'))
        if resolved:
            try:
                for fd in (proc / 'fd').iterdir():
                    if os.path.realpath(str(fd)) == resolved:
                        holders.append(dict(pid=int(proc.name), comm=comm, fd=fd.name, script_basenames=names))
            except OSError:
                unreadable_fds += 1
    capabilities = dict(systemctl=shutil.which('systemctl'), busctl=shutil.which('busctl'),
                        loginctl=shutil.which('loginctl'), euid=os.geteuid(), shutdown_executed=False)
    if capabilities['systemctl']:
        capabilities['logind_unit'] = read_command(['systemctl', 'show', 'systemd-logind.service',
                                                   '-p', 'ActiveState', '-p', 'SubState'])
    if capabilities['busctl']:
        capabilities['can_power_off_readonly_query'] = read_command([
            'busctl', 'call', 'org.freedesktop.login1', '/org/freedesktop/login1',
            'org.freedesktop.login1.Manager', 'CanPowerOff'])
    print(json.dumps(dict(audit_kind='ubuntu_host_readonly_no_board_commands',
        utc=datetime.datetime.now(datetime.timezone.utc).isoformat(), hostname=socket.gethostname(),
        machine=platform.machine(), python=sys.version.split()[0], ssh_connection_env_present=bool(os.environ.get('SSH_CONNECTION')),
        project_root=str(ROOT), paths=paths, process_matches=matches,
        uart=dict(configured_port=port, resolved_port=resolved, existing_fd_holders=holders,
                  opened_by_audit=False, holder_scan_performed=resolved is not None,
                  unreadable_fd_directories=unreadable_fds),
        proc_entries_unreadable=unreadable_cmdline, shutdown_capabilities=capabilities,
        board_contacted=False, board_commands_sent=0, models_triggered=0,
        services_stopped=0, shutdown_attempted=False, sync_attempted=False), ensure_ascii=True))


if __name__ == '__main__':
    main()
