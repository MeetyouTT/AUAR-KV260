"""Update only the verified Ubuntu SSH stanza and retain an exact backup."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys

sys.stdout.reconfigure(encoding='utf-8')

ROOT = Path(__file__).resolve().parent
CONFIG = Path.home() / '.ssh' / 'config'
original = CONFIG.read_bytes()
text = original.decode('utf-8-sig')
pattern = re.compile(r'(?ms)^Host[ \t]+aura-ubuntu[ \t]*\r?\n.*?(?=^Host[ \t]|\Z)')
matches = list(pattern.finditer(text))
assert len(matches) == 1, 'Expected exactly one concrete aura-ubuntu stanza'
old = matches[0].group()
options = {}
for line in old.splitlines()[1:]:
    parts = line.strip().split(None, 1)
    if len(parts) == 2 and not parts[0].startswith('#'):
        assert parts[0].lower() not in options, 'Duplicate SSH option'
        options[parts[0].lower()] = parts[1]
assert options.get('hostname') in ('192.168.137.141', '192.168.137.117')
assert options.get('user') == 'ghmd'
assert options.get('identityfile') == '~/.ssh/aura_5090_ubuntu_ed25519'
assert options.get('stricthostkeychecking') == 'yes'
assert options.get('userknownhostsfile') == '~/.ssh/aura_migration_known_hosts'
known = (CONFIG.parent / 'aura_migration_known_hosts').read_text('utf-8')
assert '192.168.137.141 ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIGaAmxwsztKF+n2B0me3Y9qiQ74ERdNeN9ZZPFiiiAwq' in known.splitlines()
newline = '\r\n' if '\r\n' in old else '\n'
new = re.sub(r'(?m)^([ \t]*HostName[ \t]+)[^\r\n]+', r'\g<1>192.168.137.117', old, count=1)
for name, value in [('HostKeyAlias', '192.168.137.141'), ('BindAddress', '192.168.137.1'), ('BatchMode', 'yes')]:
    if name.lower() in options:
        assert options[name.lower()] == value, f'Unexpected {name}; review first'
    else:
        new = re.sub(r'(?m)^(    HostName[^\r\n]*\r?\n)', lambda m: m.group(1) + f'    {name} {value}' + newline, new, count=1)
updated = text[:matches[0].start()] + new + text[matches[0].end():]
assert updated.replace(new, old, 1) == text, 'Unexpected change outside Ubuntu stanza'
updated_bytes = (b'\xef\xbb\xbf' if original.startswith(b'\xef\xbb\xbf') else b'') + updated.encode('utf-8')
backup = None
if updated_bytes != original:
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    backup = CONFIG.with_name('config.before-ubuntu-5090-' + stamp + '.bak')
    with backup.open('xb') as handle:
        handle.write(original)
    assert CONFIG.read_bytes() == original, 'SSH config changed concurrently'
    CONFIG.write_bytes(updated_bytes)
resolved = subprocess.run(['ssh', '-G', 'aura-ubuntu'], capture_output=True, text=True, check=True)
values = dict(line.split(' ', 1) for line in resolved.stdout.splitlines() if ' ' in line)
for name, expected in {'hostname':'192.168.137.117', 'user':'ghmd', 'port':'22', 'bindaddress':'192.168.137.1', 'hostkeyalias':'192.168.137.141', 'stricthostkeychecking':'true', 'batchmode':'yes'}.items():
    assert values.get(name) == expected, (name, values.get(name))
report = dict(updated_at_utc=datetime.now(timezone.utc).isoformat(), config_path=str(CONFIG), backup_path=str(backup) if backup else None,
              before_sha256=hashlib.sha256(original).hexdigest(), after_sha256=hashlib.sha256(updated_bytes).hexdigest(),
              only_ubuntu_stanza_changed=True, known_hosts_modified=False, private_key_copied=False,
              host='192.168.137.117', bind_address='192.168.137.1', host_key_alias='192.168.137.141',
              trusted_host_fingerprint='SHA256:tNZ7GjGBvS/wQDcvA2omrWvQAKLYIaR4/a2WaBf/Mrs',
              new_public_key_fingerprint='SHA256:gxVMk7ciwUOXO8slnAUvaUWlt5hxR62rctfL4P+P3zA')
(ROOT / 'ssh_config_preparation.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print(json.dumps(report, ensure_ascii=False, indent=2))
