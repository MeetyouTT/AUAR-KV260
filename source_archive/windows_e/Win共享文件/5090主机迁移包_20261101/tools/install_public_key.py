"""Install a new-host PUBLIC key in the current Linux account; dry-run by default."""
import argparse
import base64
import hashlib
import json
import os
from pathlib import Path
import stat
import time

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--public-key', type=Path, required=True)
p.add_argument('--apply', action='store_true')
a = p.parse_args()
raw = a.public_key.read_text('utf-8').strip()
assert '\n' not in raw and '\r' not in raw and 'PRIVATE KEY' not in raw
parts = raw.split()
assert len(parts) in (2, 3) and parts[0] == 'ssh-ed25519'
blob = base64.b64decode(parts[1], validate=True)
assert len(blob) == 51 and blob[4:15] == b'ssh-ed25519'
fingerprint = 'SHA256:'+base64.b64encode(hashlib.sha256(blob).digest()).decode().rstrip('=')
report = dict(mode='CHECK_ONLY', fingerprint=fingerprint, private_key_read=False,
              current_account_only=True, changed=False)
if a.apply:
    assert os.name == 'posix', 'Apply on the Linux destination account, not Windows.'
    directory = Path.home()/'.ssh'
    if directory.exists():
        info = directory.lstat()
        assert stat.S_ISDIR(info.st_mode) and info.st_uid == os.geteuid()
    else:
        directory.mkdir(mode=0o700)
    target = directory/'authorized_keys'
    previous = b''
    if target.exists() or target.is_symlink():
        info = target.lstat()
        assert stat.S_ISREG(info.st_mode) and info.st_uid == os.geteuid() and info.st_nlink == 1
        previous = target.read_bytes()
    exists = any(len(line.split()) >= 2 and line.split()[0:2] == parts[0:2]
                 for line in previous.decode('utf-8').splitlines())
    if not exists:
        if previous:
            backup = directory/('authorized_keys.before-5090-'+str(time.time_ns()))
            with backup.open('xb') as f:
                f.write(previous)
            backup.chmod(0o600)
        temporary = directory/('authorized_keys.new-5090-'+str(time.time_ns()))
        fd = os.open(str(temporary), os.O_WRONLY|os.O_CREAT|os.O_EXCL, 0o600)
        with os.fdopen(fd, 'wb') as f:
            f.write(previous + (b'\n' if previous and not previous.endswith(b'\n') else b'') + raw.encode()+b'\n')
            f.flush()
            os.fsync(f.fileno())
        os.replace(temporary, target)
        report['changed'] = True
    directory.chmod(0o700)
    target.chmod(0o600)
    report['mode'] = 'AUTHORIZED_IN_CURRENT_ACCOUNT'
print(json.dumps(report))
