"""Isolated validation transport. Never controls production services or devices."""
from pathlib import Path
import argparse
import hashlib
import json
import subprocess
import sys
import zipfile

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parent / '2026-10-18_board_dialogue'))
from board_ssh import ssh, KEY

REMOTE = '/home/root/aura-yuki-validation-20261030'
SCP = 'C:/Windows/System32/OpenSSH/scp.exe'


def copy_file(source, destination):
    subprocess.run([SCP, '-O', '-i', str(KEY), '-o', 'IdentitiesOnly=yes',
                    '-o', 'BatchMode=yes', '-o', 'StrictHostKeyChecking=yes',
                    '-o', 'ConnectTimeout=4', source, destination], check=True,
                   timeout=60)


def bundle():
    result = ROOT / 'board-inputs.zip'
    hashes = {}
    with zipfile.ZipFile(result, 'w', zipfile.ZIP_DEFLATED) as archive:
        for folder in ('source', 'deps', 'probe_build', 'inputs'):
            for path in sorted((ROOT / folder).rglob('*')):
                if not path.is_file():
                    continue
                relative = path.relative_to(ROOT).as_posix()
                data = path.read_bytes()
                archive.writestr(relative, data)
                hashes[relative] = hashlib.sha256(data).hexdigest()
        archive.writestr('input-sha256.json', json.dumps(hashes, indent=2))
    (ROOT / 'input-sha256.json').write_text(json.dumps(hashes, indent=2), encoding='utf-8')
    print(json.dumps({'files': len(hashes), 'bytes': result.stat().st_size}))
    return result


def upload():
    archive = bundle()
    check = f"""from pathlib import Path
root=Path({REMOTE!r})
assert not root.is_symlink()
assert str(root.resolve())=={REMOTE!r}
root.mkdir(exist_ok=True)
print('ISOLATED_ROOT_READY')
"""
    print(ssh('python3 -', check, timeout=10))
    copy_file(str(archive), f'root@192.168.50.2:{REMOTE}/board-inputs.zip')
    extract = f"""from pathlib import Path
import zipfile,json,hashlib
root=Path({REMOTE!r}).resolve()
with zipfile.ZipFile(root/'board-inputs.zip') as archive:
 for member in archive.infolist():
  target=(root/member.filename).resolve()
  assert target.is_relative_to(root)
  target.parent.mkdir(parents=True,exist_ok=True)
  target.write_bytes(archive.read(member))
hashes=json.loads((root/'input-sha256.json').read_text())
assert all(hashlib.sha256((root/p).read_bytes()).hexdigest()==h for p,h in hashes.items())
print(json.dumps({{'verified_files':len(hashes),'root':str(root)}}))
"""
    print(ssh('python3 -', extract, timeout=25))


def run(script, timeout):
    print(ssh('python3 -', Path(script).read_text(encoding='utf-8'), timeout=timeout))


def pull(name):
    path = Path(name)
    if path.is_absolute() or '..' in path.parts:
        raise ValueError('Only isolated relative evidence paths are allowed')
    destination = ROOT / 'evidence' / path
    destination.parent.mkdir(parents=True, exist_ok=True)
    copy_file(f'root@192.168.50.2:{REMOTE}/{path.as_posix()}', str(destination))
    print(destination)


def sync_probe():
    archive = ROOT / 'probe-update.zip'
    with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED) as output:
        for folder in ('probe_build', 'agent_audit', 'nose_fix', 'native_integration'):
            if not (ROOT/folder).exists():continue
            for path in sorted((ROOT / folder).rglob('*')):
                if path.is_file() and '__pycache__' not in path.parts and not any(p.startswith('build') for p in path.relative_to(ROOT).parts):
                    output.write(path, path.relative_to(ROOT).as_posix())
    copy_file(str(archive), f'root@192.168.50.2:{REMOTE}/probe-update.zip')
    script = f"""from pathlib import Path
import zipfile
root=Path({REMOTE!r}).resolve()
with zipfile.ZipFile(root/'probe-update.zip') as archive:
 for member in archive.infolist():
  target=(root/member.filename).resolve()
  assert target.is_relative_to(root)
  assert member.filename.startswith(('probe_build/','agent_audit/','nose_fix/','native_integration/'))
  target.parent.mkdir(parents=True,exist_ok=True)
  if not target.exists() or target.read_bytes()!=archive.read(member):target.write_bytes(archive.read(member))
print('PROBE_ONLY_UPDATE_COMPLETE')
"""
    print(ssh('python3 -', script, timeout=20))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('operation', choices=('upload', 'bundle', 'run', 'pull', 'sync-probe'))
    parser.add_argument('argument', nargs='?')
    parser.add_argument('--timeout', type=int, default=30)
    args = parser.parse_args()
    if args.operation == 'upload': upload()
    elif args.operation == 'sync-probe': sync_probe()
    elif args.operation == 'bundle': bundle()
    elif args.operation == 'run': run(args.argument, args.timeout)
    else: pull(args.argument)
