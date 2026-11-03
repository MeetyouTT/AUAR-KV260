#!/usr/bin/env python3
"""Bounded KV260 acceptance phases with independent evidence and recovery copies.

Runs on the board. Uses the original client, firmware, model, image and repaired
ZOCL. Firmware fixtures belong to this run; original package directories are
never renamed or deleted. No hardware failure injection or automatic reset.
"""
import concurrent.futures
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tarfile
import threading
import time

ROOT = Path('/home/root/kv260-dfx-state-boardtest-20261004')
FIRMWARE = Path('/lib/firmware/xilinx')
OFFICIAL = 'kv260-benchmark-b4096'
OLD = Path('/usr/local/lib/kv260-runtime-repair/dfx-mgrd')
OLD_SHA = 'db9c25f09f1178177884b1114c57f32c076f1e7f9cdd0d12b7a896039038a46c'
NEW = Path('/usr/local/lib/kv260-dfx-state-repair-20261003/dfx-mgrd')
NEW_SHA = '369c7fb0ddd023a7cf7af14896a7fda6036219a36f4980c73640889720c95dfd'
ARCHIVE_SHA = 'b6d8ab335041dc7f42e13e167c07c8d00e44d4469ae5278db8013b02e18d7a42'
CID = '0353445345333247805558c00401a100'
BOOT = 'a7733edd-db41-4527-b8fb-cefdcbfe7b3a'
ZOCL = '9BDC942A6014BCCBD1DCB78'
STOCK = Path('/home/root/kv260-runtime-persistent-backup-20261003/original/stock.sha256')
TEMP = Path('/run/systemd/system/dfx-mgr.service.d/90-kv260-dfx-state-validation.conf')
PERSIST = Path('/etc/systemd/system/dfx-mgr.service.d/20-kv260-dfx-state-repaired.conf')
TEMP_CONTENT = ('# Temporary acceptance override created by kv260-dfx-state-boardtest-20261004\n'
                '[Service]\nExecStart=\nExecStart=' + str(NEW) + '\n'
                'StandardOutput=append:' + str(ROOT / 'manager.stdout') + '\n'
                'StandardError=append:' + str(ROOT / 'manager.stderr') + '\n')
PERSIST_CONTENT = ('# Board-verified state lifecycle fix; previous runtime drop-in is retained.\n'
                   '[Service]\nExecStart=\nExecStart=' + str(NEW) + '\n')
TOP5 = [(258, '0.949879'), (270, '0.00931229'), (259, '0.00821807'),
        (257, '0.00498451'), (279, '0.00388194')]
CLASSIFY = ['/home/root/Vitis-AI/examples/vai_library/samples/classification/test_jpeg_classification',
            '/usr/share/vitis_ai_library/models/resnet18/resnet18.xmodel',
            '/home/root/kv260-test-20261001/pytorch-resnet-dog.jpg']
CLIENT = '/usr/bin/dfx-mgr-client'
TREE = 'kv260-sv-tree'
PEER = 'kv260-sv-tree-peer'
ACTIVE = 'kv260-sv-active'


def read(path):
    return Path(path).read_text().strip()


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def save(path, obj):
    Path(path).write_text(json.dumps(obj, indent=2, ensure_ascii=False) + '\n')


class Evidence:
    def __init__(self, phase):
        self.phase = phase
        self.out = ROOT / 'evidence' / (phase + '-' + str(time.monotonic_ns()))
        self.out.mkdir(parents=True, exist_ok=False)
        self.commands = []
        self.checks = {}
        self.lock = threading.Lock()
        self.seq = 0
        self.start = time.monotonic()

    def run(self, name, argv, timeout=90, require=True):
        start = time.monotonic()
        with self.lock:
            self.seq += 1
            prefix = '%05d-%s' % (self.seq, name)
        try:
            p = subprocess.run(argv, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=timeout)
            rc, stdout, stderr = p.returncode, p.stdout, p.stderr
            error = None
        except subprocess.TimeoutExpired as exc:
            rc, stdout, stderr = None, exc.stdout or b'', exc.stderr or b''
            error = 'timeout'
        (self.out / (prefix + '.stdout')).write_bytes(stdout)
        (self.out / (prefix + '.stderr')).write_bytes(stderr)
        record = {'id': prefix, 'argv': argv, 'rc': rc, 'error': error,
                  'started_monotonic': start, 'elapsed_seconds': time.monotonic() - start,
                  'stdout_sha256': hashlib.sha256(stdout).hexdigest(),
                  'stderr_sha256': hashlib.sha256(stderr).hexdigest()}
        with self.lock:
            self.commands.append(record)
            with (self.out / 'commands.jsonl').open('a') as f:
                f.write(json.dumps(record) + '\n')
        if require and rc != 0:
            raise RuntimeError('Command failed: %s rc=%s' % (prefix, rc))
        return {'rc': rc, 'stdout': stdout.decode(errors='replace'), 'stderr': stderr.decode(errors='replace'),
                'elapsed_seconds': record['elapsed_seconds']}

    def check(self, name, condition):
        self.checks[name] = bool(condition)
        save(self.out / 'checks.json', self.checks)
        if not condition:
            raise RuntimeError('Check failed: ' + name)

    def finish(self, error=None):
        status = {'phase': self.phase, 'evidence': str(self.out), 'boot_id': read('/proc/sys/kernel/random/boot_id'),
                  'started_monotonic': self.start, 'elapsed_seconds': time.monotonic() - self.start,
                  'checks': self.checks, 'complete': error is None, 'error': error,
                  'driver_sha256': sha(__file__), 'commands': len(self.commands)}
        save(self.out / 'summary.json', status)
        save(ROOT / ('phase-' + self.phase + '.json'), status)
        print(json.dumps(status, ensure_ascii=False), flush=True)


def guard(e, allow_new_boot=False):
    e.check('root', os.geteuid() == 0)
    e.check('spare_card_identity', read('/sys/class/block/mmcblk1/device/cid') == CID)
    e.check('tested_kernel', read('/proc/sys/kernel/osrelease') == '5.15.36-xilinx-v2022.2')
    e.check('expected_boot', allow_new_boot or read('/proc/sys/kernel/random/boot_id') == BOOT)
    e.check('repaired_zocl', read('/sys/module/zocl/srcversion') == ZOCL)
    e.check('xgq_ert_enabled', read('/sys/module/zocl/parameters/enable_xgq_ert') == '1')
    e.check('old_recovery_binary_intact', sha(OLD) == OLD_SHA)


def props(e):
    r = e.run('service-properties', ['systemctl', 'show', 'dfx-mgr.service', '-p', 'MainPID', '-p', 'ActiveState',
               '-p', 'SubState', '-p', 'Result', '-p', 'ExecStart', '-p', 'ExecStartPre', '-p', 'DropInPaths',
               '-p', 'Requires', '-p', 'After', '-p', 'ExecMainStatus'])
    return dict(line.split('=', 1) for line in r['stdout'].splitlines() if '=' in line)


def manager(e, path):
    p = props(e)
    pid = int(p['MainPID'])
    e.check('manager_running_' + path.parent.name, p['ActiveState'] == 'active' and p['SubState'] == 'running' and pid > 0)
    e.check('manager_exact_executable_' + path.parent.name, Path('/proc/%d/exe' % pid).resolve() == path)
    e.check('preserved_driver_dependency', 'kv260-repaired-zocl.service' in p['Requires'].split() and
            'kv260-repaired-zocl.service' in p['After'].split())
    managers = []
    for process in Path('/proc').iterdir():
        if not process.name.isdigit():
            continue
        try:
            if read(process / 'comm') == 'dfx-mgrd':
                managers.append(process)
        except OSError:
            continue  # Short-lived unrelated processes can exit during inventory.
    e.check('single_manager_process', len(managers) == 1)
    return pid


def watch_state(pid):
    infos = {}
    for p in Path('/proc/%d/fdinfo' % pid).iterdir():
        text = p.read_text()
        if 'inotify wd:' in text:
            infos[p.name] = text
    return {'pid': pid, 'watch_count': sum(t.count('inotify wd:') for t in infos.values()),
            'inotify_fd_count': len(infos), 'fd_count': len(list(Path('/proc/%d/fd' % pid).iterdir())),
            'fdinfo': infos, 'proc_status': read('/proc/%d/status' % pid),
            'overlays': sorted(p.name for p in Path('/sys/kernel/config/device-tree/overlays').iterdir()),
            'render_nodes': sorted(p.name for p in Path('/dev/dri').glob('renderD*'))}


def packages(e, name='packages'):
    r = e.run(name, [CLIENT, '-listPackage'], timeout=12)
    rows = {}
    for line in r['stdout'].splitlines():
        fields = line.split()
        if len(fields) == 6 and fields[1] in ('XRT_FLAT', 'PL_FLAT', 'SIHA_PL_DFX', 'XRT_AIE_DFX'):
            rows[fields[0]] = {'base': fields[2], 'type': fields[1], 'slot': fields[-1]}
    if not rows:
        raise RuntimeError('No parsed packages')
    return rows


def stock(e):
    result = e.run('original-26-hashes', ['sha256sum', '-c', str(STOCK)])
    e.check('original_26_unchanged', result['stdout'].count(': OK\n') == 26)
    return result


def functional(e, label):
    query = e.run(label + '-query', ['xdputil', 'query'])
    q = json.loads(query['stdout'])
    expected = {'DPU Arch': 'DPUCZDX8G_ISA1_B4096', 'DPU Frequency (MHz)': 300,
                'cu_addr': '0xa0010000', 'fingerprint': '0x101000056010407'}
    e.check(label + '_dpu_profile', q['DPU IP Spec']['DPU Core Count'] == 1 and len(q['kernels']) == 1 and
            all(q['kernels'][0][k] == v for k, v in expected.items()))
    result = e.run(label + '-classification', CLASSIFY)
    top5 = [(int(a), b) for a, b in re.findall(r'r.index (\d+) .*?r.score ([0-9.eE+-]+)',
                                            result['stdout'] + result['stderr'])]
    e.check(label + '_same_image_top5', top5 == TOP5)
    save(e.out / (label + '-top5.json'), top5)


def no_hardware_clients(e):
    e.check('zocl_no_module_references', read('/sys/module/zocl/refcnt') == '0')
    for p in Path('/sys/kernel/debug/dri').glob('*/clients'):
        if p.parent.name == '0':
            continue  # Display Xorg does not own the ZOCL accelerator.
        text = p.read_text()
        (e.out / ('drm-' + p.parent.name + '-clients.txt')).write_text(text)
        e.check('no_accelerator_drm_clients_' + p.parent.name, len(text.splitlines()) <= 1)


def unload(e, label='unload', explicit=False):
    no_hardware_clients(e)
    argv = [CLIENT, '-remove', '0'] if explicit else ['xmutil', 'unloadapp']
    r = e.run(label, argv)
    e.check(label + '_protocol_success', bool(re.search(r'returns:\s*0\s*\(Ok\)', r['stdout'])))
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        if not list(Path('/sys/kernel/config/device-tree/overlays').iterdir()) and not list(Path('/dev/dri').glob('renderD*')):
            break
        time.sleep(.05)
    e.check(label + '_overlay_and_render_removed', not list(Path('/sys/kernel/config/device-tree/overlays').iterdir())
            and not list(Path('/dev/dri').glob('renderD*')))
    r = e.run(label + '-uio-state', [CLIENT, '-listUIO', '0'])
    e.check(label + '_runtime_no_active_design', 'No active design' in r['stdout'])


def load(e, name=OFFICIAL, label='load'):
    r = e.run(label, ['xmutil', 'loadapp', name])
    e.check(label + '_protocol_success', 'loaded to slot 0' in r['stdout'] and 'Error' not in r['stdout'])
    rows = packages(e, label + '-packages')
    e.check(label + '_slot_zero', name in rows and rows[name]['slot'] == '0,')
    e.check(label + '_physical_overlay_and_render', len(list(Path('/sys/kernel/config/device-tree/overlays').iterdir())) == 1
            and len(list(Path('/dev/dri').glob('renderD*'))) == 1)


def stop(e):
    e.run('manager-stop', ['systemctl', 'stop', 'dfx-mgr.service'])
    p = props(e)
    e.check('manager_stopped', p['MainPID'] == '0' and p['ActiveState'] == 'inactive')


def require_phase(e, phase):
    p = ROOT / ('phase-' + phase + '.json')
    e.check('previous_phase_' + phase, p.is_file() and json.loads(p.read_text())['complete'])


def backup(e):
    guard(e)
    pid = manager(e, OLD)
    stock(e)
    e.check('no_existing_overrides', not TEMP.exists() and not PERSIST.exists() and not NEW.exists())
    e.check('official_active', packages(e)[OFFICIAL]['slot'] == '0,')
    no_hardware_clients(e)
    out = ROOT / 'backup'
    out.mkdir(mode=0o700, exist_ok=False)
    paths = [str(OLD), '/usr/local/lib/kv260-runtime-repair/zocl.ko',
             '/usr/local/lib/kv260-runtime-repair/load-repaired-zocl.sh', '/etc/vart.conf', '/etc/fstab',
             '/etc/dfx-mgrd/daemon.conf', '/etc/dfx-mgrd/default_firmware', '/lib/systemd/system/dfx-mgr.service',
             '/etc/systemd/system/dfx-mgr.service.d/10-kv260-repaired.conf',
             '/etc/systemd/system/kv260-repaired-zocl.service', str(STOCK)]
    for directory in ['/etc/systemd/system/dfx-mgr.service.d', '/run/systemd/system/dfx-mgr.service.d']:
        for p in Path(directory).glob('*.conf'):
            if str(p) not in paths:
                paths.append(str(p))
    hashes = {}
    for name in paths:
        p = Path(name)
        dest = out / name.lstrip('/')
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(p, dest)
        hashes[name] = sha(p)
        e.check('backup_' + p.name, sha(dest) == hashes[name])
    save(out / 'original-hashes.json', hashes)
    e.run('unit-before', ['systemctl', 'cat', 'dfx-mgr.service'])
    e.run('driver-unit-before', ['systemctl', 'cat', 'kv260-repaired-zocl.service'])
    e.run('kernel-before', ['dmesg'])
    save(out / 'runtime-before.json', watch_state(pid))
    functional(e, 'baseline')
    save(ROOT / 'recovery.json', {'boot_id': BOOT, 'cid': CID, 'manager': str(OLD), 'manager_sha256': OLD_SHA,
         'backup_hashes': hashes, 'backup_evidence': str(e.out), 'default_app': OFFICIAL})
    e.run('flush-backup', ['sync'])


def unpack(e):
    guard(e)
    require_phase(e, 'backup')
    archive = ROOT / 'staging/candidate.tar.gz'
    e.check('archive_sha256', sha(archive) == ARCHIVE_SHA)
    target = ROOT / 'staging/extracted'
    target.mkdir(exist_ok=False)
    with tarfile.open(archive) as tar:
        members = tar.getmembers()
        e.check('archive_154_regular_members', len(members) == 154 and all(m.isfile() for m in members))
        e.check('archive_safe_paths', all(not Path(m.name).is_absolute() and '..' not in Path(m.name).parts for m in members))
        tar.extractall(target)
    checked = 0
    for line in (target / 'SHA256SUMS').read_text().splitlines():
        digest, name = line.split(None, 1)
        name = name.lstrip('*')
        e.check('bundle_' + name, sha(target / name) == digest)
        checked += 1
    e.check('candidate_daemon_sha256', sha(target / 'bin/dfx-mgrd') == NEW_SHA)
    e.check('candidate_path_new', not NEW.exists())
    NEW.parent.mkdir(mode=0o755, parents=True, exist_ok=False)
    shutil.copy2(target / 'bin/dfx-mgrd', NEW)
    NEW.chmod(0o755)
    e.check('installed_candidate_hash', sha(NEW) == NEW_SHA)
    save(e.out / 'unpacked.json', {'regular_members': len(members), 'manifest_members_checked': checked,
         'archive_sha256': ARCHIVE_SHA, 'candidate_sha256': sha(NEW), 'client_deployed': False})
    stock(e)


def start(e):
    guard(e)
    require_phase(e, 'unpack')
    manager(e, OLD)
    e.check('candidate_hash', sha(NEW) == NEW_SHA)
    e.check('temporary_path_absent', not TEMP.exists())
    unload(e, 'baseline-unload')
    stop(e)
    TEMP.parent.mkdir(parents=True, exist_ok=True)
    with TEMP.open('x') as f:
        f.write(TEMP_CONTENT)
    save(ROOT / 'temporary-dropin.json', {'path': str(TEMP), 'sha256': sha(TEMP), 'content': TEMP_CONTENT})
    e.run('daemon-reload', ['systemctl', 'daemon-reload'])
    p = props(e)
    e.check('parsed_candidate_execstart', str(NEW) in p['ExecStart'])
    e.check('parsed_driver_dependency', 'kv260-repaired-zocl.service' in p['Requires'].split() and
            'kv260-repaired-zocl.service' in p['After'].split())
    e.run('merged-candidate-unit', ['systemctl', 'cat', 'dfx-mgr.service'])
    e.run('candidate-start', ['systemctl', 'start', 'dfx-mgr.service'])
    pid = manager(e, NEW)
    rows = packages(e)
    e.check('default_official_app_loaded', rows[OFFICIAL]['slot'] == '0,')
    state = watch_state(pid)
    save(ROOT / 'candidate-baseline.json', state)
    e.check('initial_watch_baseline_five', state['watch_count'] == 5 and state['inotify_fd_count'] == 1)
    functional(e, 'candidate-first')
    stock(e)


def await_rows(e, predicate, label):
    end = time.monotonic() + 5
    while time.monotonic() < end:
        rows = packages(e, label)
        if predicate(rows):
            return rows
        time.sleep(.02)
    raise RuntimeError('Package reconciliation timeout: ' + label)


def owned_tree(path):
    if path != FIRMWARE / TREE or not (path / '.kv260-state-fixture').is_file():
        raise RuntimeError('Deletion target is not this run fixture')
    if (path / '.kv260-state-fixture').read_text() != str(ROOT):
        raise RuntimeError('Fixture ownership mismatch')
    if any(p.is_symlink() for p in path.rglob('*')):
        raise RuntimeError('Unexpected symlink in fixture')
    shutil.rmtree(path)


def make_tree(path, iteration):
    path.mkdir(exist_ok=False)
    (path / '.kv260-state-fixture').write_text(str(ROOT))
    save(path / 'shell.json', {'shell_type': 'PL_DFX', 'num_pl_slots': 2 if iteration % 2 == 0 else 4, 'num_aie_slots': 0})
    for i in range(3):
        child = path / ('svrm%d' % i)
        child.mkdir()
        for j in range(2):
            grandchild = child / ('svrm%d_slot%d' % (i, j))
            grandchild.mkdir()
            save(grandchild / 'accel.json', {'accel_type': 'SIHA_PL_DFX'})


def stress(e):
    guard(e)
    require_phase(e, 'start')
    pid = manager(e, NEW)
    baseline = json.loads((ROOT / 'candidate-baseline.json').read_text())
    e.check('same_candidate_pid', pid == baseline['pid'])
    e.check('fixture_names_free', not (FIRMWARE / TREE).exists() and not (FIRMWARE / PEER).exists())
    staging = ROOT / 'fixtures'
    staging.mkdir(exist_ok=False)
    peer = FIRMWARE / PEER
    peer.mkdir()
    (peer / '.kv260-state-fixture').write_text(str(ROOT))
    save(peer / 'shell.json', {'shell_type': 'PL_FLAT', 'num_pl_slots': 1, 'num_aie_slots': 0})
    await_rows(e, lambda rows: PEER in rows, 'peer-present')
    count = baseline['watch_count']
    e.check('peer_one_extra_watch', watch_state(pid)['watch_count'] == count + 1)
    latencies = []

    def reader(worker):
        for n in range(250):
            begin = time.monotonic()
            rows = packages(e, 'parallel-list-%d-%d' % (worker, n))
            if rows.get(OFFICIAL, {}).get('slot') != '0,' or PEER not in rows:
                raise RuntimeError('Official runtime or neighbor package lost during queries')
            latencies.append(time.monotonic() - begin)

    def writer():
        cycles = []
        for n in range(100):
            outside = staging / ('tree-prepared-%03d' % n)
            make_tree(outside, n)
            outside.rename(FIRMWARE / TREE)
            rows = await_rows(e, lambda r: all(r.get('svrm%d' % i, {}).get('base') == TREE for i in range(3)),
                              'tree-added-%03d' % n)
            loaded_count = watch_state(pid)['watch_count']
            if loaded_count != count + 11:
                raise RuntimeError('Expected all child and grandchild watches: %d' % loaded_count)
            # Exercise child rename while another thread is repeatedly listing.
            child = FIRMWARE / TREE / 'svrm2'
            child.rename(FIRMWARE / TREE / 'svrm2x')
            await_rows(e, lambda r: 'svrm2x' in r and 'svrm2' not in r, 'child-renamed-%03d' % n)
            owned_tree(FIRMWARE / TREE)
            await_rows(e, lambda r: not any(v['base'] == TREE for v in r.values()) and PEER in r,
                       'parent-deleted-%03d' % n)
            after = watch_state(pid)['watch_count']
            if after != count + 1:
                raise RuntimeError('Descendant watch leak after parent deletion: %d' % after)
            cycles.append({'cycle': n, 'added_watch_count': loaded_count, 'removed_watch_count': after,
                           'children': 3, 'grandchildren': 6})
            save(e.out / 'directory-cycles.json', cycles)
        return cycles

    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as pool:
        futures = [pool.submit(reader, n) for n in range(4)]
        directory_future = pool.submit(writer)
        for future in futures:
            future.result()
        cycles = directory_future.result()
    e.check('1000_concurrent_package_queries', len(latencies) == 1000)
    e.check('100_multilevel_parent_deletions', len(cycles) == 100)
    e.check('neighbor_retained', PEER in packages(e, 'neighbor-final'))
    peer.rename(staging / PEER)
    await_rows(e, lambda r: PEER not in r, 'neighbor-moved-out')
    after = watch_state(pid)
    save(e.out / 'final-state.json', after)
    e.check('all_fixture_watches_reclaimed', after['watch_count'] == count and after['fd_count'] == baseline['fd_count'])
    e.check('manager_pid_unchanged', int(props(e)['MainPID']) == pid)
    latencies.sort()
    save(e.out / 'query-latency.json', {'count': len(latencies), 'min_seconds': latencies[0],
         'median_seconds': latencies[500], 'p95_seconds': latencies[949], 'p99_seconds': latencies[989],
         'max_seconds': latencies[-1], 'timeout_seconds': 12, 'all_seconds': latencies})
    functional(e, 'after-directory-stress')
    stock(e)


def active_move(e):
    guard(e)
    require_phase(e, 'stress')
    pid = manager(e, NEW)
    baseline = json.loads((ROOT / 'candidate-baseline.json').read_text())
    target = FIRMWARE / ACTIVE
    outside = ROOT / 'fixtures' / ACTIVE
    e.check('active_fixture_paths_free', not target.exists() and not outside.exists())
    source = FIRMWARE / OFFICIAL
    shutil.copytree(source, target)
    (target / '.kv260-state-fixture').write_text(str(ROOT))
    e.check('active_copy_all_bytes_match', all(sha(target / p.name) == sha(p) for p in source.iterdir() if p.is_file()))
    await_rows(e, lambda r: ACTIVE in r, 'active-fixture-present')
    unload(e, 'official-unload-for-active-test')
    load(e, ACTIVE, 'dedicated-copy-load')
    functional(e, 'dedicated-copy')
    state_loaded = watch_state(pid)
    target.rename(outside)
    await_rows(e, lambda r: ACTIVE not in r, 'active-directory-disappeared')
    disappeared = watch_state(pid)
    e.check('moved_package_watches_reclaimed', disappeared['watch_count'] == baseline['watch_count'])
    e.check('hardware_preserved_until_explicit_unload', disappeared['overlays'] == state_loaded['overlays']
            and disappeared['render_nodes'] == state_loaded['render_nodes'])
    r = e.run('uio-while-package-missing', [CLIENT, '-listUIO', '0'])
    e.check('runtime_slot_retained', 'No active design' not in r['stdout'] and 'invalid' not in r['stdout'])
    # Existing VART path points to the moved copy. Do not rewrite it or infer an
    # inference failure from missing input files. Query the still-loaded DPU only.
    query = e.run('dpu-still-present', ['xdputil', 'query'])
    e.check('dpu_remains_real_loaded', json.loads(query['stdout'])['DPU IP Spec']['DPU Core Count'] == 1)
    unload(e, 'explicit-unload-missing-package', explicit=True)
    outside.rename(target)
    await_rows(e, lambda r: r.get(ACTIVE, {}).get('slot') == '-1', 'same-name-reintroduced-inactive')
    load(e, ACTIVE, 'same-name-reuse-load')
    functional(e, 'same-name-reuse')
    unload(e, 'same-name-reuse-unload')
    target.rename(outside)
    await_rows(e, lambda r: ACTIVE not in r, 'active-fixture-removed-final')
    load(e, OFFICIAL, 'official-restored-after-active-test')
    functional(e, 'after-active-disappearance')
    save(e.out / 'loaded-state.json', state_loaded)
    save(e.out / 'disappeared-state.json', disappeared)
    stock(e)
    e.check('final_watch_baseline', watch_state(pid)['watch_count'] == baseline['watch_count'])


def cycles(e):
    guard(e)
    require_phase(e, 'active-move')
    pid = manager(e, NEW)
    baseline = json.loads((ROOT / 'candidate-baseline.json').read_text())
    for n in range(10):
        unload(e, 'cycle-%02d-unload' % n)
        load(e, OFFICIAL, 'cycle-%02d-load' % n)
        functional(e, 'cycle-%02d' % n)
        e.check('cycle-%02d-watch-baseline' % n, watch_state(pid)['watch_count'] == baseline['watch_count'])
    for slot in ['255', '-2']:
        r = e.run('invalid-remove-' + slot, [CLIENT, '-remove', slot])
        e.check('invalid_slot_' + slot + '_rejected', bool(re.search(r'returns:\s*-1\s*\(Error\)', r['stdout'])))
    functional(e, 'after-invalid-slot-requests')
    stock(e)
    state = watch_state(pid)
    save(e.out / 'final-state.json', state)
    e.check('watch_fd_pid_stable', state['watch_count'] == baseline['watch_count'] and
            state['fd_count'] == baseline['fd_count'] and int(props(e)['MainPID']) == pid)
    e.run('kernel-after-candidate', ['dmesg'])
    e.run('service-journal-candidate', ['journalctl', '-b', '-u', 'dfx-mgr.service', '--no-pager', '-o', 'short-monotonic'])


def restore(e):
    guard(e)
    require_phase(e, 'cycles')
    manager(e, NEW)
    e.check('only_our_temporary_override', TEMP.read_text() == TEMP_CONTENT and not PERSIST.exists())
    unload(e, 'candidate-unload-before-restore')
    stop(e)
    TEMP.unlink()
    e.run('restore-daemon-reload', ['systemctl', 'daemon-reload'])
    p = props(e)
    e.check('original_parsed_execstart_restored', str(OLD) in p['ExecStart'] and str(NEW) not in p['ExecStart'])
    e.run('original-manager-start', ['systemctl', 'start', 'dfx-mgr.service'])
    pid = manager(e, OLD)
    e.check('official_default_restored', packages(e)[OFFICIAL]['slot'] == '0,')
    functional(e, 'restored-old-manager')
    stock(e)
    recovery = json.loads((ROOT / 'recovery.json').read_text())
    e.check('all_recovery_files_preserved', all(sha(p) == digest for p, digest in recovery['backup_hashes'].items()))
    save(e.out / 'restored-state.json', watch_state(pid))
    e.run('kernel-after-restoration', ['dmesg'])
    e.run('service-journal-after-restoration', ['journalctl', '-b', '-u', 'dfx-mgr.service', '--no-pager', '-o', 'short-monotonic'])


def persist(e):
    guard(e)
    require_phase(e, 'restore')
    review = json.loads((ROOT / 'acceptance-review.json').read_text())
    e.check('host_review_of_all_board_evidence_passed', review['passed'] and review['candidate_sha256'] == NEW_SHA
            and review['boot_id'] == BOOT)
    manager(e, OLD)
    e.check('candidate_still_exact', sha(NEW) == NEW_SHA)
    e.check('persistent_dropin_new', not PERSIST.exists() and not TEMP.exists())
    unload(e, 'old-unload-before-persistent-switch')
    stop(e)
    with PERSIST.open('x') as f:
        f.write(PERSIST_CONTENT)
        f.flush()
        os.fsync(f.fileno())
    e.run('persistent-daemon-reload', ['systemctl', 'daemon-reload'])
    p = props(e)
    e.check('persistent_parsed_execstart', str(NEW) in p['ExecStart'] and str(PERSIST) in p['DropInPaths'])
    e.check('persistent_driver_dependency', 'kv260-repaired-zocl.service' in p['Requires'].split() and
            'kv260-repaired-zocl.service' in p['After'].split())
    e.run('persistent-merged-unit', ['systemctl', 'cat', 'dfx-mgr.service'])
    e.run('persistent-candidate-start', ['systemctl', 'start', 'dfx-mgr.service'])
    pid = manager(e, NEW)
    functional(e, 'persistent-service-restart')
    stock(e)
    save(e.out / 'persistent-state.json', watch_state(pid))
    save(ROOT / 'persistent-install.json', {'path': str(PERSIST), 'content': PERSIST_CONTENT,
         'sha256': sha(PERSIST), 'candidate_sha256': sha(NEW), 'previous_manager': str(OLD), 'boot_id_before': BOOT})
    e.run('flush-persistent-install', ['sync'])


def postboot(e):
    guard(e, allow_new_boot=True)
    require_phase(e, 'persist')
    e.check('new_boot_id', read('/proc/sys/kernel/random/boot_id') != BOOT)
    e.check('temporary_override_gone', not TEMP.exists())
    e.check('persistent_config_exact', PERSIST.read_text() == PERSIST_CONTENT)
    e.check('candidate_hash_exact', sha(NEW) == NEW_SHA)
    pid = manager(e, NEW)
    p = props(e)
    e.check('persistent_override_selected', str(PERSIST) in p['DropInPaths'] and str(NEW) in p['ExecStart'])
    loader = e.run('driver-loader-status', ['systemctl', 'show', 'kv260-repaired-zocl.service',
                   '-p', 'ActiveState', '-p', 'SubState', '-p', 'Result', '-p', 'ExecMainStatus'])
    e.check('driver_loader_success', all(x in loader['stdout'] for x in
            ['ActiveState=active', 'SubState=exited', 'Result=success', 'ExecMainStatus=0']))
    e.check('official_app_auto_loaded', packages(e)[OFFICIAL]['slot'] == '0,')
    functional(e, 'postboot')
    stock(e)
    state = watch_state(pid)
    save(e.out / 'postboot-state.json', state)
    e.check('postboot_watch_baseline_five', state['watch_count'] == 5)
    e.run('boot-kernel', ['dmesg'])
    e.run('boot-journal', ['journalctl', '-b', '--no-pager', '-o', 'short-monotonic'])
    e.run('boot-service-journal', ['journalctl', '-b', '-u', 'dfx-mgr.service', '-u', 'kv260-repaired-zocl.service',
          '--no-pager', '-o', 'short-monotonic'])
    e.run('failed-units', ['systemctl', '--failed', '--no-pager', '--plain'])
    e.run('boot-mount', ['findmnt', '-n', '-o', 'SOURCE,FSTYPE,TARGET', '/boot'])
    e.check('fstab_preserved', sha('/etc/fstab') == '580d18ee47a5dbe98b86ccec7670518c00fe8bc7b58990e186a00d9f559329f0')


def export(e):
    # Copy every artifact, including failures, then verify a frozen manifest.
    evidence = ROOT / 'exports'
    evidence.mkdir(exist_ok=True)
    target = evidence / ('board-evidence-' + str(time.monotonic_ns()) + '.tar.gz')
    members = [p for p in ROOT.rglob('*') if p.is_file() and not p.is_symlink() and
               not p.is_relative_to(evidence) and not p.is_relative_to(ROOT / 'staging/extracted') and
               not p.is_relative_to(ROOT / 'fixtures') and p != ROOT / 'staging/candidate.tar.gz' and
               not p.is_relative_to(e.out)]
    manifest = {str(p.relative_to(ROOT)): {'bytes': p.stat().st_size, 'sha256': sha(p)} for p in members}
    save(e.out / 'export-manifest.json', manifest)
    with tarfile.open(target, 'x:gz') as tar:
        for p in members:
            tar.add(p, arcname=str(p.relative_to(ROOT)), recursive=False)
        tar.add(e.out / 'export-manifest.json', arcname='EXPORT_MANIFEST.json')
    result = {'archive': str(target), 'bytes': target.stat().st_size, 'sha256': sha(target), 'files': len(manifest)}
    save(ROOT / 'LATEST_EXPORT.json', result)
    print('EXPORT ' + json.dumps(result), flush=True)


def main():
    phase = sys.argv[1]
    phases = {'backup': backup, 'unpack': unpack, 'start': start, 'stress': stress,
              'active-move': active_move, 'cycles': cycles, 'restore': restore,
              'persist': persist, 'postboot': postboot, 'export': export}
    if phase not in phases:
        raise SystemExit('Unknown phase')
    e = Evidence(phase)
    try:
        phases[phase](e)
    except Exception as exc:
        e.finish('%s: %s' % (type(exc).__name__, exc))
        raise
    e.finish()


if __name__ == '__main__':
    main()
