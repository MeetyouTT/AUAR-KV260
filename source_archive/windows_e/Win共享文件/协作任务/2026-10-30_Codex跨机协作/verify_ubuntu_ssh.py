"""Loopback SSH test with a temporary local key, removed before returning."""
import datetime
import fcntl
import json
import os
from pathlib import Path
import shlex
import subprocess
import tempfile
import uuid

root = Path(__file__).resolve().parent
authorized = Path.home()/'.ssh/authorized_keys'
report = dict(schema_version=1,status='CHECKING',host='127.0.0.1',port=22,user='ghmd',
              scope='Ubuntu loopback SSH only; Windows network path not verified',
              checks=[],temporary_key_shared=False,app_server_started=False)
before = authorized.read_bytes()
test_line = None
try:
    with tempfile.TemporaryDirectory(prefix='aura-codex-ssh-local-') as directory:
        temporary = Path(directory)
        key = temporary/'local_test_key'
        subprocess.run(['ssh-keygen','-q','-t','ed25519','-N','','-C',
                        'aura-local-ssh-preflight-'+uuid.uuid4().hex,'-f',str(key)],check=True)
        test_line = key.with_suffix('.pub').read_bytes().strip()
        with authorized.open('r+b') as stream:
            fcntl.flock(stream,fcntl.LOCK_EX)
            current = stream.read()
            stream.seek(0,2)
            stream.write((b'\n' if current and not current.endswith(b'\n') else b'')+test_line+b'\n')
            stream.flush()
            os.fsync(stream.fileno())
        public = Path('/etc/ssh/ssh_host_ed25519_key.pub').read_text().split()
        known_hosts = temporary/'known_hosts'
        known_hosts.write_text('127.0.0.1 '+public[0]+' '+public[1]+'\n')
        prefix = ['ssh','-T','-i',str(key),'-o','IdentitiesOnly=yes','-o','BatchMode=yes',
                  '-o','StrictHostKeyChecking=yes','-o','UserKnownHostsFile='+str(known_hosts),
                  '-o','ClearAllForwardings=yes','-o','ConnectTimeout=5','-p','22','ghmd@127.0.0.1']
        commands = [('codex_path','type -P codex'),('codex_version','codex --version'),
                    ('codex_authenticated','codex login status'),
                    ('login_shell_codex','/bin/bash -lc '+shlex.quote('type -P codex')),
                    ('project_exists','test -d '+shlex.quote('/home/ghmd/Win共享文件/语音共享文件'))]
        for name,command in commands:
            result = subprocess.run(prefix+[command],text=True,stdout=subprocess.PIPE,
                                    stderr=subprocess.PIPE,timeout=20)
            report['checks'].append(dict(name=name,exit_code=result.returncode,
                                         stdout=result.stdout.strip()[:1000],stderr=result.stderr.strip()[:1000]))
            assert result.returncode == 0, 'SSH check failed: '+name
        report['status'] = 'PASS_LOCAL_SSH'
except Exception as exc:
    report.update(status='FAIL_LOCAL_SSH',error=type(exc).__name__+': '+str(exc))
finally:
    if test_line is not None:
        with authorized.open('r+b') as stream:
            fcntl.flock(stream,fcntl.LOCK_EX)
            current = stream.read()
            expected = before+(b'\n' if before and not before.endswith(b'\n') else b'')+test_line+b'\n'
            if current == expected:
                restored = before
            else:
                restored = b''.join(line for line in current.splitlines(keepends=True)
                                    if line.strip() != test_line)
            stream.seek(0)
            stream.write(restored)
            stream.truncate()
            stream.flush()
            os.fsync(stream.fileno())
        report['temporary_authorized_key_removed'] = test_line not in authorized.read_bytes().splitlines()
    report['windows_key_content_preserved'] = before in authorized.read_bytes()
    report['updated_at'] = datetime.datetime.now(datetime.timezone.utc).isoformat()
    target = root/'ubuntu-local-ssh-verification.json'
    temporary_report = target.with_suffix('.json.tmp')
    temporary_report.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    os.replace(str(temporary_report),str(target))
print(json.dumps(report,ensure_ascii=False))
raise SystemExit(0 if report['status'] == 'PASS_LOCAL_SSH' else 1)
