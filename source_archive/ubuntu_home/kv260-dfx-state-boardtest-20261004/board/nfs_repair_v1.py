#!/usr/bin/env python3
"""Scoped NFS server startup repair, preserving the working KV260 runtime."""
import gzip
import json
import os
from pathlib import Path
import shutil
import sys
import tarfile
import time

import validate_v5 as v

ROOT = Path('/home/root/kv260-platform-warnings-20261004/nfs')
v.ROOT = ROOT
PRE_BOOT = '01ca88c1-93b6-414f-9646-774482d4b2f0'
MOUNT = 'proc-fs-nfsd.mount'
SERVERS = ['nfs-server.service', 'nfs-mountd.service']
CLIENTS = ['rpcbind.service', 'rpcbind.socket', 'nfs-statd.service', 'nfs-idmapd.service']
CONF = Path('/etc/systemd/system/proc-fs-nfsd.mount.d/20-kv260-nfs-capability.conf')
CONTENT = ('# KV260: the current kernel has CONFIG_NFSD unset; NFS clients remain enabled.\n'
           '# If NFS server support is introduced, review this guard and restore the server services.\n'
           '[Unit]\nConditionPathExists=/sys/module/nfsd\n')
LINKS = [Path('/etc/systemd/system/multi-user.target.wants') / unit for unit in SERVERS]
PROTECTED = [Path('/lib/systemd/system') / unit for unit in [MOUNT] + SERVERS + CLIENTS]
PROTECTED += [Path('/lib/systemd/system/sysinit.target.wants/proc-fs-nfsd.mount'),
              Path('/etc/systemd/system/multi-user.target.wants/nfs-statd.service'),
              Path('/etc/systemd/system/multi-user.target.wants/rpcbind.service'),
              Path('/etc/systemd/system/sockets.target.wants/rpcbind.socket'),
              Path('/etc/systemd/system/nfsserver.service'),
              Path('/etc/systemd/system/mountnfs.service'),
              Path('/etc/systemd/system/nfscommon.service'),
              Path('/etc/fstab'), Path('/etc/exports'), v.NEW, v.OLD, v.PERSIST,
              Path('/etc/systemd/system/dfx-mgr.service.d/10-kv260-repaired.conf'),
              Path('/etc/systemd/system/kv260-repaired-zocl.service'),
              Path('/usr/local/lib/kv260-runtime-repair/zocl.ko'),
              Path('/usr/local/lib/kv260-runtime-repair/load-repaired-zocl.sh')]


class Evidence(v.Evidence):
    def finish(self, error=None):
        status = {'phase': self.phase, 'evidence': str(self.out),
                  'boot_id': v.read('/proc/sys/kernel/random/boot_id'),
                  'started_monotonic': self.start, 'elapsed_seconds': time.monotonic() - self.start,
                  'checks': self.checks, 'complete': error is None, 'error': error,
                  'controller_sha256': v.sha(__file__), 'driver_sha256': v.sha(v.__file__),
                  'commands': len(self.commands)}
        v.save(self.out / 'summary.json', status)
        v.save(ROOT / ('phase-' + self.phase + '.json'), status)
        print(json.dumps(status, ensure_ascii=False), flush=True)


def metadata(path):
    if path.is_symlink():
        return {'kind': 'symlink', 'target': os.readlink(path)}
    if path.is_file():
        return {'kind': 'file', 'bytes': path.stat().st_size, 'sha256': v.sha(path)}
    if not path.exists():
        return {'kind': 'absent'}
    raise RuntimeError('Unexpected path type: ' + str(path))


def unit(e, name, label):
    fields = ['Id', 'UnitFileState', 'LoadState', 'ActiveState', 'SubState', 'Result',
              'MainPID', 'ConditionResult', 'ConditionTimestampMonotonic', 'Conditions',
              'DropInPaths', 'ExecMount', 'Requires', 'After']
    argv = ['systemctl', 'show', name]
    for field in fields:
        argv += ['-p', field]
    result = e.run(label + '-' + name, argv)
    return dict(line.split('=', 1) for line in result['stdout'].splitlines() if '=' in line)


def guard(e, new_boot=False):
    v.guard(e, allow_new_boot=True)
    if not new_boot:
        e.check('same_pre_repair_boot', v.read('/proc/sys/kernel/random/boot_id') == PRE_BOOT)
    e.check('same_candidate', v.sha(v.NEW) == v.NEW_SHA)
    e.check('persistent_manager_config', v.PERSIST.read_text() == v.PERSIST_CONTENT and not v.TEMP.exists())
    e.check('same_validation_driver', v.sha(v.__file__) ==
            '276c81dfba6c282afaa1f911ae30ba4ff72c112504ead4c1643e53ba34629ddf')
    return v.manager(e, v.NEW)


def no_server_use(e):
    config = gzip.decompress(Path('/proc/config.gz').read_bytes()).decode()
    e.check('nfs_server_unsupported_client_supported', '# CONFIG_NFSD is not set\n' in config
            and 'CONFIG_NFS_FS=y\n' in config and not Path('/sys/module/nfsd').exists())
    paths = [Path('/etc/exports')] + list(Path('/etc/exports.d').glob('*.exports'))
    exports = sum(bool(line.strip()) and not line.lstrip().startswith('#')
                  for p in paths if p.is_file() for line in p.read_text().splitlines())
    e.check('no_configured_nfs_exports', exports == 0)
    result = e.run('existing-nfs-client-mounts', ['findmnt', '-rn', '-t', 'nfs,nfs4', '-o', 'FSTYPE,TARGET'], require=False)
    e.check('no_mounted_nfs_filesystems', result['rc'] == 1 and not result['stdout'] and not result['stderr'])


def recovery():
    return json.loads((ROOT / 'recovery.json').read_text())


def protected(e, before):
    e.check('protected_vendor_client_runtime_files_unchanged',
            all(metadata(Path(path)) == value for path, value in before['protected'].items()))


def backup(e):
    pid = guard(e)
    no_server_use(e)
    e.check('no_existing_recovery', not (ROOT / 'recovery.json').exists())
    e.check('new_dropin_path', not CONF.exists() and not CONF.is_symlink())
    states = {name: unit(e, name, 'before') for name in [MOUNT] + SERVERS + CLIENTS}
    e.check('expected_original_server_enable_state', all(states[name]['UnitFileState'] == 'enabled'
            and states[name]['ActiveState'] == 'inactive' for name in SERVERS))
    e.check('expected_original_mount_failure', states[MOUNT]['ActiveState'] == 'failed')
    e.check('expected_enable_links', all(p.is_symlink() and p.resolve() == Path('/lib/systemd/system') / p.name for p in LINKS))
    originals = {str(p): metadata(p) for p in PROTECTED}
    for path, item in originals.items():
        if item['kind'] == 'file':
            target = ROOT / 'backup' / path.lstrip('/')
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, target)
            e.check('backup_' + path, v.sha(target) == item['sha256'])
    original = {'boot_id': PRE_BOOT, 'manager_pid': pid, 'states': states, 'protected': originals,
                'enable_links': {str(p): metadata(p) for p in LINKS},
                'configuration': {'path': str(CONF), 'content': CONTENT},
                'watch_state': v.watch_state(pid)}
    v.stock(e)
    e.check('official_app_active_before', v.packages(e)[v.OFFICIAL]['slot'] == '0,')
    v.save(ROOT / 'recovery.json', original)
    v.save(e.out / 'recovery.json', original)
    e.run('flush-backup', ['sync'])


def rollback(e, before):
    if CONF.exists():
        if CONF.read_text() != CONTENT:
            raise RuntimeError('Drop-in was changed outside this repair; rollback stopped')
        CONF.unlink()  # Only the exact newly created file, with verified content.
    for name, item in before['enable_links'].items():
        p = Path(name)
        if p.is_symlink():
            if metadata(p) != item:
                raise RuntimeError('Enable link changed outside this repair: ' + name)
        elif not p.exists():
            os.symlink(item['target'], p)
        else:
            raise RuntimeError('Unexpected enable path during rollback: ' + name)
    e.run('rollback-daemon-reload', ['systemctl', 'daemon-reload'])
    protected(e, before)
    e.run('flush-rollback', ['sync'])
    v.save(e.out / 'rollback.json', {'configuration_restored': True,
                                    'original_mount_failure_not_retriggered': True})


def check_install(e, before, postboot=False):
    pid = guard(e, new_boot=postboot)
    e.check('configuration_exact', CONF.read_text() == CONTENT)
    e.check('enable_links_absent', all(not p.exists() and not p.is_symlink() for p in LINKS))
    protected(e, before)
    after = {name: unit(e, name, 'after') for name in [MOUNT] + SERVERS + CLIENTS}
    e.check('servers_disabled_and_inactive', all(after[name]['UnitFileState'] == 'disabled'
            and after[name]['ActiveState'] == 'inactive' for name in SERVERS))
    mount = after[MOUNT]
    e.check('mount_dropin_parsed', str(CONF) in mount['DropInPaths'] and '/sys/module/nfsd' in mount['Conditions'])
    e.check('unsupported_mount_skipped', mount['ActiveState'] == 'inactive'
            and mount['ConditionResult'] == 'no' and int(mount['ConditionTimestampMonotonic']) > 0)
    for name in CLIENTS:
        e.check('client_preserved_' + name, all(after[name].get(key) == before['states'][name].get(key)
                for key in ['UnitFileState', 'ActiveState', 'SubState']))
    if not postboot:
        e.check('manager_pid_preserved', pid == before['manager_pid'])
        e.check('client_pids_preserved', all(after[name].get('MainPID') == before['states'][name].get('MainPID')
                for name in CLIENTS))
    e.check('official_default_active', v.packages(e)[v.OFFICIAL]['slot'] == '0,')
    v.functional(e, 'postboot-nfs' if postboot else 'after-nfs-fix')
    v.stock(e)
    state = v.watch_state(pid)
    e.check('hardware_and_watch_state_preserved', state['watch_count'] == 5 and state['inotify_fd_count'] == 1
            and state['overlays'] == before['watch_state']['overlays']
            and state['render_nodes'] == before['watch_state']['render_nodes'])
    e.run('tpm-capabilities', ['tpm2_getcap', '-T', 'device:/dev/tpmrm0', 'properties-fixed'])
    failed = e.run('failed-units', ['systemctl', 'list-units', '--failed', '--no-legend', '--plain', '--no-pager'])
    e.check('no_failed_units', not failed['stdout'].strip())
    v.save(e.out / 'unit-states.json', after)
    v.save(e.out / 'runtime-state.json', state)
    return state


def apply(e):
    v.require_phase(e, 'backup')
    before = recovery()
    guard(e)
    no_server_use(e)
    protected(e, before)
    e.check('new_configuration_still_absent', not CONF.exists() and not CONF.is_symlink())
    changed = False
    try:
        CONF.parent.mkdir(parents=True, exist_ok=True)
        with CONF.open('x') as f:
            changed = True
            f.write(CONTENT)
            f.flush()
            os.fsync(f.fileno())
        e.run('disable-unused-server-startup', ['systemctl', 'disable', '--now'] + SERVERS)
        e.run('load-capability-guard', ['systemctl', 'daemon-reload'])
        parsed = unit(e, MOUNT, 'parsed')
        e.check('capability_condition_loaded_before_probe', str(CONF) in parsed['DropInPaths']
                and '/sys/module/nfsd' in parsed['Conditions'] and not Path('/sys/module/nfsd').exists())
        e.run('reset-previous-nfs-failure', ['systemctl', 'reset-failed', MOUNT] + SERVERS)
        e.run('verify-mount-condition-skips', ['systemctl', 'start', MOUNT])
        state = check_install(e, before)
        e.run('kernel-after-fix', ['dmesg'])
        e.run('nfs-journal-after-fix', ['journalctl', '-b', '-u', MOUNT, '-u', SERVERS[0], '-u', SERVERS[1],
              '--no-pager', '-o', 'short-monotonic'])
        e.run('flush-installed-configuration', ['sync'])
        v.save(ROOT / 'installed.json', {'boot_id_before': PRE_BOOT, 'manager_pid': state['pid'],
               'configuration_sha256': v.sha(CONF), 'configuration_path': str(CONF),
               'server_services_disabled': SERVERS, 'mount_condition': '/sys/module/nfsd',
               'client_services_preserved': CLIENTS})
    except Exception:
        if changed:
            rollback(e, before)
        raise


def postboot(e):
    v.require_phase(e, 'apply')
    e.check('fresh_boot_after_install', v.read('/proc/sys/kernel/random/boot_id') != PRE_BOOT)
    no_server_use(e)
    check_install(e, recovery(), postboot=True)
    e.run('boot-kernel', ['dmesg'])
    e.run('boot-journal', ['journalctl', '-b', '--no-pager', '-o', 'short-monotonic'])
    e.run('nfs-boot-journal', ['journalctl', '-b', '-u', MOUNT, '-u', SERVERS[0], '-u', SERVERS[1],
          '--no-pager', '-o', 'short-monotonic'])
    e.run('boot-mount', ['findmnt', '-n', '-o', 'SOURCE,FSTYPE,TARGET', '/boot'])


def prepare_coldboot(e):
    v.require_phase(e, 'apply')
    guard(e)
    protected(e, recovery())
    e.check('configuration_before_poweroff', CONF.read_text() == CONTENT)
    v.stock(e)
    v.unload(e, 'unload-before-nfs-coldboot')
    v.stop(e)
    e.run('flush-before-poweroff', ['sync'])


def export(e):
    directory = ROOT / 'exports'
    directory.mkdir(exist_ok=True)
    target = directory / ('nfs-evidence-' + str(time.monotonic_ns()) + '.tar.gz')
    paths = [p for p in ROOT.rglob('*') if p.is_file() and not p.is_symlink()
             and not p.is_relative_to(directory) and not p.is_relative_to(e.out)]
    manifest = {str(p.relative_to(ROOT)): {'bytes': p.stat().st_size, 'sha256': v.sha(p)} for p in paths}
    v.save(e.out / 'export-manifest.json', manifest)
    with tarfile.open(target, 'x:gz') as tar:
        for p in paths:
            tar.add(p, arcname=str(p.relative_to(ROOT)), recursive=False)
        tar.add(__file__, arcname='CONTROLLER.py', recursive=False)
        tar.add(e.out / 'export-manifest.json', arcname='EXPORT_MANIFEST.json', recursive=False)
    print('EXPORT ' + json.dumps({'archive': str(target), 'bytes': target.stat().st_size,
                                  'sha256': v.sha(target), 'files': len(manifest)}), flush=True)


def main():
    phase = sys.argv[1]
    phases = {'backup': backup, 'apply': apply, 'postboot': postboot,
              'prepare-coldboot': prepare_coldboot, 'export': export}
    e = Evidence(phase)
    try:
        phases[phase](e)
    except Exception as exc:
        e.finish(type(exc).__name__ + ': ' + str(exc))
        raise
    e.finish()


if __name__ == '__main__':
    main()
