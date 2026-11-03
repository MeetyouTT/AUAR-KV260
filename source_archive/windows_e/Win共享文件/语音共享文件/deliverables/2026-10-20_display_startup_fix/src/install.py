"""Install or roll back the reviewed next-start display files without restarting."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def command(args):
    return subprocess.check_output(args, stderr=subprocess.STDOUT, timeout=12).decode()


def replace(path, data, mode):
    temporary = path.with_name(path.name+'.aura-display-new')
    with temporary.open('xb') as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())
    os.chmod(str(temporary), mode)
    os.replace(str(temporary), str(path))
    descriptor = os.open(str(path.parent), os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('apply', 'rollback'))
    args = parser.parse_args()
    here = Path(__file__).resolve().parent
    manifest = json.loads((here/'manifest.json').read_text())
    backup = here/'backup'
    assert os.geteuid() == 0
    assert Path('/sys/block/mmcblk1/device/cid').read_text().strip() == manifest['cid']
    for name, expected in manifest['payload'].items():
        assert digest(here/name) == expected, 'Payload hash mismatch: '+name
    if args.action == 'rollback':
        records = json.loads((backup/'files.json').read_text())
        # Check everything before reverting either file. Never clobber later edits.
        for record in records:
            assert digest(record['target']) == manifest['payload'][record['source']]
            assert digest(backup/record['source']) == record['sha256']
        for record in reversed(records):
            replace(Path(record['target']), (backup/record['source']).read_bytes(), record['mode'])
        print(json.dumps({'status':'ROLLED_BACK_NEXT_START_ONLY', 'restarted':False}))
        return

    assert Path('/proc/sys/kernel/random/boot_id').read_text().strip() == manifest['boot_id']
    state_args = ['systemctl','show','aura-avatar-ui.service','-p','MainPID','--value']
    pid = command(state_args).strip()
    argv = (Path('/proc')/pid/'cmdline').read_bytes().decode().split('\0')
    assert manifest['launcher'] in argv
    assert argv[argv.index('--config')+1] == manifest['config']
    assert digest(manifest['config']) == manifest['config_sha256']
    # The candidate reads and validates all current GUI/audio/component hashes.
    preflight = json.loads(command(['/usr/bin/python3','-B',str(here/'launcher.py'),
        '--config',manifest['config'],'--preflight']))
    targets = [('launcher.py', manifest['launcher'], manifest['launcher_sha256']),
               ('xorg.conf', '/etc/X11/xorg.conf', manifest['xorg_sha256'])]
    for name, target, expected in targets:
        path = Path(target)
        assert not path.is_symlink() and digest(path) == expected, 'Baseline changed: '+target
    backup.mkdir(exist_ok=False)
    records = []
    for name, target, expected in targets:
        path = Path(target)
        shutil.copy2(str(path), str(backup/name))
        records.append({'source':name,'target':target,'sha256':expected,
                        'mode':path.stat().st_mode & 0o777})
    (backup/'files.json').write_text(json.dumps(records,indent=2)+'\n')
    applied = []
    try:
        for record in records:
            assert digest(record['target']) == record['sha256']
            applied.append(record)
            replace(Path(record['target']), (here/record['source']).read_bytes(), record['mode'])
        assert command(state_args).strip() == pid, 'Live supervisor changed during installation'
        assert digest(manifest['config']) == manifest['config_sha256']
        for record in records:
            assert digest(record['target']) == manifest['payload'][record['source']]
    except Exception:
        for record in reversed(applied):
            if digest(record['target']) == manifest['payload'][record['source']]:
                replace(Path(record['target']), (backup/record['source']).read_bytes(), record['mode'])
        raise
    result = {'status':'INSTALLED_NEXT_START_PHYSICAL_PENDING', 'supervisor_pid':int(pid),
        'boot_id':manifest['boot_id'], 'preflight':preflight, 'backup':str(backup),
        'targets':{record['target']:digest(record['target']) for record in records},
        'display_commands_sent':0,'movement_commands_sent':0,'restarted':False,
        'cold_boot_verified':False,'physical_panel_verified':False}
    (here/'installed.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result),flush=True)


if __name__ == '__main__':
    main()
