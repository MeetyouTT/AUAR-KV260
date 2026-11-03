#!/usr/bin/env python3
"""Check the installed FPGA environment in an isolated evidence directory."""
import datetime
import hashlib
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
M3 = Path('/home/ghmd/kv260-m3-axilite-20261002')
TOOLS = Path('/home/ghmd/Xilinx_2022.2')
SETTINGS = TOOLS / 'Vitis/2022.2/settings64.sh'
PETA_SETTINGS = Path('/home/ghmd/petalinux/2022.2/settings.sh')


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def save(path, value):
    Path(path).write_text(json.dumps(value, indent=2, ensure_ascii=False) + '\n')


def main():
    phase = sys.argv[1]
    if phase not in ['inventory', 'versions', 'vivado', 'xsct', 'petalinux']:
        raise SystemExit('Unknown phase')
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')
    out = ROOT / 'evidence' / (stamp + '-' + phase)
    out.mkdir(parents=True, exist_ok=False)
    status = {'phase': phase, 'evidence': str(out), 'started_utc': stamp,
              'complete': False, 'commands': [], 'checks': {},
              'controller_sha256': sha(__file__), 'board_accessed': False,
              'existing_project_modified': False}

    def check(name, value):
        status['checks'][name] = bool(value)
        if not value:
            raise RuntimeError('Check failed: ' + name)

    def run(label, argv, settings=None, timeout=180):
        actual = argv
        if settings:
            actual = ['/bin/bash', '--noprofile', '--norc', '-c',
                      'aura_env_entry=$1; shift; aura_env_command=( "$@" ); set --; source "$aura_env_entry" || exit $?; exec "${aura_env_command[@]}"',
                      'aura-fpga-environment', str(settings)] + argv
        env = os.environ.copy()
        env['AURA_FPGA_REVIEW_OUT'] = str(out)
        started = time.monotonic()
        with (out / (label + '.stdout')).open('xb') as stdout, (out / (label + '.stderr')).open('xb') as stderr:
            proc = subprocess.Popen(actual, cwd=str(out), env=env, stdout=stdout, stderr=stderr, start_new_session=True)
            timed_out = False
            try:
                rc = proc.wait(timeout=timeout)
            except subprocess.TimeoutExpired:
                timed_out = True
                os.killpg(proc.pid, signal.SIGTERM)
                try:
                    rc = proc.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    os.killpg(proc.pid, signal.SIGKILL)
                    rc = proc.wait()
        record = {'id': label, 'argv': actual, 'rc': rc, 'timeout': timed_out,
                  'elapsed_seconds': time.monotonic() - started,
                  'stdout_sha256': sha(out / (label + '.stdout')),
                  'stderr_sha256': sha(out / (label + '.stderr'))}
        status['commands'].append(record)
        save(out / 'status.json', status)
        print(json.dumps({'id': label, 'rc': rc, 'elapsed_seconds': round(record['elapsed_seconds'], 2)}), flush=True)
        check(label + '_rc', rc == 0 and not timed_out)
        return (out / (label + '.stdout')).read_text(errors='replace')

    try:
        if phase == 'inventory':
            old = json.loads((M3 / 'evidence/artifacts.json').read_text())
            artifacts = []
            for item in old['artifacts']:
                p = M3 / item['path']
                actual = sha(p)
                passed = p.stat().st_size == item['bytes'] and actual == item['sha256']
                artifacts.append(dict(item, actual_sha256=actual, passed=passed))
                check('artifact_' + item['role'], passed)
            review = json.loads((M3 / 'evidence/host_review_summary.json').read_text())
            inputs = []
            for item in review['build_identity']['inputs']:
                actual = sha(M3 / item['path'])
                inputs.append(dict(item, actual_sha256=actual, passed=actual == item['sha256']))
                check('input_' + item['path'], actual == item['sha256'])
            paths = [SETTINGS, TOOLS / 'Vivado/2022.2/settings64.sh',
                     TOOLS / 'Vitis_HLS/2022.2/settings64.sh', PETA_SETTINGS]
            resource = {'settings_files': {str(p): {'exists': p.is_file(), 'sha256': sha(p) if p.is_file() else None} for p in paths},
                        'cpu_count': os.cpu_count(), 'disk_free_bytes': shutil.disk_usage(ROOT).free,
                        'meminfo': {line.split(':', 1)[0]: line.split(':', 1)[1].strip()
                                    for line in Path('/proc/meminfo').read_text().splitlines()
                                    if line.startswith(('MemTotal:', 'MemAvailable:', 'SwapTotal:', 'SwapFree:'))},
                        'unsourced_path_tools': {name: shutil.which(name) for name in ['vivado', 'v++', 'xsct', 'petalinux-build']}}
            save(out / 'inventory.json', {'artifacts': artifacts, 'inputs': inputs,
                                        'historical_host_review': review, 'resources': resource})
            check('all_four_settings_files_present', all(p.is_file() for p in paths))
            run('host-version', ['uname', '-srmo'])
            run('host-os', ['cat', '/etc/os-release'])
            run('host-build-dependencies', ['dpkg-query', '-W', '-f=${Package} ${Status} ${Version}\n',
                                         'build-essential', 'flex', 'bison', 'libssl-dev', 'git', 'python3'])
        elif phase == 'versions':
            a = run('vivado-version', [str(TOOLS / 'Vivado/2022.2/bin/vivado'), '-version'], SETTINGS)
            check('vivado_2022_2', 'Vivado v2022.2' in a)
            a = run('vpp-version', [str(TOOLS / 'Vitis/2022.2/bin/v++'), '--version'], SETTINGS)
            check('vpp_2022_2', 'v2022.2' in a)
            a = run('hls-version', [str(TOOLS / 'Vitis_HLS/2022.2/bin/vitis_hls'), '-version'], SETTINGS)
            check('hls_2022_2', '2022.2' in a)
        elif phase == 'vivado':
            source = ROOT / 'scripts/vivado_check.tcl'
            shutil.copy2(source, out / source.name)
            a = run('vivado-capability', [str(TOOLS / 'Vivado/2022.2/bin/vivado'), '-mode', 'batch',
                    '-source', str(out / source.name), '-log', str(out / 'vivado.log'),
                    '-journal', str(out / 'vivado.jou')], SETTINGS, timeout=300)
            for marker in ['AURA_K26_PART=xck26-sfvc784-2LV-c', 'AURA_KV260_BOARD=',
                           'AURA_CLOCK_PRODUCTS_READY', 'AURA_M3_SYNTHESIS_COMPLETE', 'AURA_FPGA_ENV_COMPLETE']:
                check(marker, marker in a)
        elif phase == 'xsct':
            source = ROOT / 'scripts/xsct_check.tcl'
            shutil.copy2(source, out / source.name)
            a = run('xsct-hsi', [str(TOOLS / 'Vitis/2022.2/bin/xsct'), '-nodisp', str(out / source.name)], SETTINGS)
            check('xsct_hsi_reads_existing_xsa', 'AURA_XSA_READ_COMPLETE' in a)
        elif phase == 'petalinux':
            code = ('import os,shutil,json; print(json.dumps({"version":os.environ.get("PETALINUX_VER"),'
                    '"petalinux_build":shutil.which("petalinux-build"),"petalinux_config":shutil.which("petalinux-config")}))')
            a = run('petalinux-environment', ['python3', '-c', code], PETA_SETTINGS)
            item = json.loads(a.strip().splitlines()[-1])
            check('petalinux_2022_2_loaded', item['version'] == '2022.2' and bool(item['petalinux_build']) and bool(item['petalinux_config']))
        status['complete'] = True
    except Exception as exc:
        status['error'] = type(exc).__name__ + ': ' + str(exc)
    finally:
        status['finished_utc'] = datetime.datetime.now(datetime.timezone.utc).isoformat()
        save(out / 'status.json', status)
        save(ROOT / ('CURRENT_' + phase.upper() + '.json'), status)
    print(json.dumps({'phase': phase, 'complete': status['complete'], 'error': status.get('error'), 'evidence': str(out)}, ensure_ascii=False), flush=True)
    raise SystemExit(0 if status['complete'] else 1)


if __name__ == '__main__':
    main()
