"""Collect read-only Ubuntu connection evidence using strict key-only SSH."""
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import sys

sys.stdout.reconfigure(encoding='utf-8')

ROOT = Path(__file__).resolve().parent
payload = r'''
import base64
import hashlib
import json
import os
from pathlib import Path
import pwd
import socket
import stat
import subprocess

def run(args):
    result = subprocess.run(args, capture_output=True, text=True, timeout=20)
    return {'exit_code': result.returncode, 'stdout': result.stdout.strip()[:1800], 'stderr': result.stderr.strip()[:500]}

project = Path('/home/ghmd/Win共享文件/语音共享文件')
shell = pwd.getpwuid(os.getuid()).pw_shell
auth = subprocess.run([shell, '-lc', 'codex login status >/dev/null 2>&1'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=20)
key_blob = 'AAAAC3NzaC1lZDI1NTE5AAAAIKREQRi56xo8VT/bjs99j0nWC4bdon2Br/pyRWCn/l5n'
authorized = Path.home()/'.ssh'/'authorized_keys'
key_present = any(key_blob in line.split() for line in authorized.read_text('utf-8').splitlines())
report = {
 'hostname': socket.gethostname(), 'user': pwd.getpwuid(os.getuid()).pw_name,
 'ssh_connection': os.environ.get('SSH_CONNECTION'),
 'remote_host_key': run(['ssh-keygen', '-lf', '/etc/ssh/ssh_host_ed25519_key.pub']),
 'return_route_to_windows': run(['ip', '-4', 'route', 'get', '192.168.137.1']),
 'codex_in_command_shell': run([shell, '-c', 'command -v codex']),
 'codex_in_login_shell': run([shell, '-lc', 'command -v codex']),
 'codex_version_login_shell': run([shell, '-lc', 'codex --version']),
 'codex_expected_file_executable': os.access('/home/ghmd/.local/bin/codex', os.X_OK),
 'codex_expected_file_realpath': str(Path('/home/ghmd/.local/bin/codex').resolve()),
 'codex_authenticated': auth.returncode == 0,
 'project_path': str(project), 'project_exists': project.is_dir(),
 'project_accessible': os.access(project, os.R_OK|os.X_OK),
 'new_public_key_authorized': key_present,
 'ssh_directory_mode': oct(stat.S_IMODE((Path.home()/'.ssh').stat().st_mode)),
 'authorized_keys_mode': oct(stat.S_IMODE(authorized.stat().st_mode)),
 'private_keys_or_auth_database_read': False,
 'board_or_model_services_modified': False,
}
print(json.dumps(report, ensure_ascii=False))
'''
started = datetime.now(timezone.utc).isoformat()
result = subprocess.run(['ssh', '-v', '-T', '-o', 'BatchMode=yes', '-o', 'PasswordAuthentication=no',
                         '-o', 'PreferredAuthentications=publickey', '-o', 'StrictHostKeyChecking=yes',
                         'aura-ubuntu', 'python3', '-'], input=payload, encoding='utf-8', errors='replace',
                        capture_output=True, timeout=50)
(ROOT/'ssh_verification.log').write_text(result.stderr, encoding='utf-8')
report = dict(started_at_utc=started, finished_at_utc=datetime.now(timezone.utc).isoformat(),
              ssh_exit_code=result.returncode, key_only_login=False, strict_host_key_verified=False)
if result.returncode == 0:
    report['remote'] = json.loads(result.stdout)
    report['key_only_login'] = 'using "publickey"' in result.stderr
    report['strict_host_key_verified'] = 'known and matches the ED25519 host key' in result.stderr
else:
    report['error'] = result.stderr[-2000:]
remote=report.get('remote', {})
report['ssh_and_remote_prerequisites_verified'] = all([
    report['key_only_login'], report['strict_host_key_verified'],
    remote.get('user') == 'ghmd', remote.get('ssh_connection','').split()[::2] == ['192.168.137.1','192.168.137.117'],
    remote.get('codex_authenticated'), remote.get('project_exists'), remote.get('project_accessible'),
    remote.get('new_public_key_authorized'), remote.get('codex_version_login_shell',{}).get('exit_code') == 0,
])
(ROOT/'ssh_verification.json').write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
print(json.dumps(report, ensure_ascii=False, indent=2))
raise SystemExit(0 if report['ssh_and_remote_prerequisites_verified'] else 1)
