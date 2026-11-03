"""Append only the supplied Windows public key; never handle private keys."""
import base64
import datetime
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import struct

root = Path(__file__).resolve().parent
source = root/'windows-codex.pub'
lines = [line.strip() for line in source.read_text(encoding='utf-8-sig').splitlines() if line.strip()]
assert len(lines) == 1
parts = lines[0].split()
assert len(parts) >= 2 and parts[0] == 'ssh-ed25519'
raw = base64.b64decode(parts[1],validate=True)
length = struct.unpack('>I',raw[:4])[0]
assert raw[4:4+length] == b'ssh-ed25519'
assert struct.unpack('>I',raw[4+length:8+length])[0] == 32 and len(raw) == 8+length+32
fingerprint = 'SHA256:'+base64.b64encode(hashlib.sha256(raw).digest()).decode().rstrip('=')
assert fingerprint == 'SHA256:2e0xLhkeWwz48xIv0QqIfeTNeXoEX6sgjt2yo5ftvlc'
ssh = Path.home()/'.ssh'
assert not ssh.is_symlink()
ssh.mkdir(mode=0o700,exist_ok=True)
assert ssh.stat().st_uid == os.getuid()
ssh.chmod(0o700)
target = ssh/'authorized_keys'
fd = os.open(str(target),os.O_RDWR | os.O_APPEND | os.O_CREAT | os.O_NOFOLLOW,0o600)
try:
    fcntl.flock(fd,fcntl.LOCK_EX)
    info = os.fstat(fd)
    assert stat.S_ISREG(info.st_mode) and info.st_uid == os.getuid()
    os.fchmod(fd,0o600)
    with os.fdopen(os.dup(fd),'rb') as stream:
        before = stream.read()
    pattern = re.compile(rb'(?:^|[ \t])ssh-ed25519[ \t]+([A-Za-z0-9+/=]+)(?:[ \t]|$)')
    matches = [match.group(1) for line in before.splitlines() if not line.lstrip().startswith(b'#')
               for match in [pattern.search(line)] if match]
    added = parts[1].encode() not in matches
    if added:
        payload = (b'\n' if before and not before.endswith(b'\n') else b'')+lines[0].encode()+b'\n'
        assert os.write(fd,payload) == len(payload)
        os.fsync(fd)
    with target.open('rb') as stream:
        after = stream.read()
    assert after.startswith(before)
finally:
    os.close(fd)
report = dict(schema_version=1,updated_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
              status='PUBLIC_KEY_INSTALLED',user=Path.home().name,authorized_keys=str(target),
              key_fingerprint=fingerprint,key_added=added,ssh_directory_mode='0700',
              authorized_keys_mode='0600',existing_content_preserved=True,
              private_key_read=False,credentials_copied=False)
temporary = root/'ubuntu-key-preparation.json.tmp'
temporary.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
os.replace(str(temporary),str(root/'ubuntu-key-preparation.json'))
print(json.dumps(report,ensure_ascii=False))
