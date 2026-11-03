#!/usr/bin/env python3
"""Independently re-read tool checks and preserve every unsuccessful attempt."""
import datetime
import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
M3 = Path('/home/ghmd/kv260-m3-axilite-20261002')


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def main():
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')
    directory = ROOT / 'reviews' / stamp
    directory.mkdir(parents=True, exist_ok=False)
    result = {'recorded_utc': stamp, 'passed': False, 'checks': {},
              'board_accessed': False, 'full_hardware_rebuild_performed': False,
              'full_linux_image_build_performed': False}

    def check(name, value):
        result['checks'][name] = bool(value)
        if not value:
            raise RuntimeError('Check failed: ' + name)

    try:
        controllers = {sha(p) for p in (ROOT / 'scripts').glob('review_tools*.py')}
        phases = {}
        for name in ['inventory', 'versions', 'vivado', 'xsct', 'petalinux']:
            status = json.loads((ROOT / ('CURRENT_' + name.upper() + '.json')).read_text())
            out = Path(status['evidence'])
            check(name + '_complete', status['complete'] and not status.get('error')
                  and all(status['checks'].values()))
            check(name + '_frozen_status', json.loads((out / 'status.json').read_text()) == status)
            check(name + '_controller_provenance', status['controller_sha256'] in controllers)
            for item in status['commands']:
                check(name + '_' + item['id'] + '_rc', item['rc'] == 0 and not item['timeout'])
                for stream in ['stdout', 'stderr']:
                    check(name + '_' + item['id'] + '_' + stream,
                          sha(out / (item['id'] + '.' + stream)) == item[stream + '_sha256'])
            phases[name] = {'status': status, 'out': out}
        inventory = json.loads((phases['inventory']['out'] / 'inventory.json').read_text())
        check('all_11_original_artifacts_present_and_intact', len(inventory['artifacts']) == 11
              and all(item['passed'] and sha(M3 / item['path']) == item['sha256']
                      for item in inventory['artifacts']))
        check('all_11_original_source_configuration_inputs_unchanged', len(inventory['inputs']) == 11
              and all(item['passed'] and sha(M3 / item['path']) == item['sha256']
                      for item in inventory['inputs']))
        check('settings_files_unchanged', all(sha(path) == item['sha256']
              for path, item in inventory['resources']['settings_files'].items()))
        deps = (phases['inventory']['out'] / 'host-build-dependencies.stdout').read_text().splitlines()
        check('all_six_host_packages_installed', len(deps) == 6 and all(' install ok installed ' in line for line in deps))
        versions = phases['versions']['out']
        check('vivado_current_version_2022_2', re.search(r'^Vivado v2022\.2 ', (versions / 'vivado-version.stdout').read_text(), re.M))
        check('vpp_current_version_2022_2', 'v++ v2022.2' in (versions / 'vpp-version.stdout').read_text())
        check('hls_current_version_2022_2', 'v2022.2' in (versions / 'hls-version.stdout').read_text())
        vivado = phases['vivado']['out']
        stdout = (vivado / 'vivado-capability.stdout').read_text()
        lines = stdout.splitlines()
        for marker in ['AURA_K26_PART=xck26-sfvc784-2LV-c', 'AURA_KV260_BOARD=xilinx.com:kv260_som:part0:1.4',
                       'AURA_CLOCK_PRODUCTS_READY', 'AURA_M3_SYNTHESIS_COMPLETE', 'AURA_FPGA_ENV_COMPLETE']:
            check('actual_tool_output_' + marker, marker in lines)
        check('synthesis_license_checkout_succeeded', "Got license for feature 'Synthesis' and/or device 'xck26'" in stdout)
        check('no_vivado_error_or_critical_warning', not re.search(r'^(?:ERROR:|CRITICAL WARNING:)', stdout, re.M))
        utilization = (vivado / 'm3_current_synthesis_utilization.rpt').read_text()
        check('m3_current_synthesis_resources', re.search(r'\| CLB LUTs\*\s*\|\s*54\s*\|', utilization)
              and re.search(r'\| CLB Registers\s*\|\s*118\s*\|', utilization))
        xsct = (phases['xsct']['out'] / 'xsct-hsi.stdout').read_text().splitlines()
        check('xsct_read_existing_xsa', 'AURA_XSA_READ_COMPLETE' in xsct and 'AURA_XSA_CELL_COUNT=175' in xsct)
        peta = (phases['petalinux']['out'] / 'petalinux-environment.stdout').read_text()
        peta_item = json.loads(peta.strip().splitlines()[-1])
        check('petalinux_current_version_and_entrypoints', peta_item['version'] == '2022.2'
              and peta_item['petalinux_build'].endswith('/bin/petalinux-build')
              and peta_item['petalinux_config'].endswith('/bin/petalinux-config'))
        for marker in ['INFO: Checking free disk space', 'INFO: Checking installed tools',
                       'INFO: Checking installed development libraries', 'INFO: Checking network and other services']:
            check('petalinux_env_check_' + marker, marker in peta)
        failures = [json.loads(p.read_text()) for p in (ROOT / 'evidence').glob('*/status.json')
                    if not json.loads(p.read_text())['complete']]
        check('two_unsuccessful_checker_attempts_preserved', len(failures) == 2 and all(x['phase'] == 'petalinux' for x in failures))
        result['preserved_checker_failures'] = failures
        result['phase_evidence'] = {name: str(item['out']) for name, item in phases.items()}
        result['resources'] = inventory['resources']
        result['historical_timing'] = inventory['historical_host_review']['timing']
        result['historical_utilization'] = inventory['historical_host_review']['resources']
        result['petalinux_tftp_warning'] = 'No tftp server found' in peta
        result['fpga_core_environment_verified'] = True
        result['full_motion_platform_completed'] = False
        result['passed'] = True
    except Exception as exc:
        result['error'] = type(exc).__name__ + ': ' + str(exc)
    destination = directory / 'review.json'
    destination.write_text(json.dumps(result, indent=2, ensure_ascii=False) + '\n')
    (ROOT / 'CURRENT_REVIEW.json').write_text(json.dumps({'passed': result['passed'], 'review': str(destination)}, indent=2) + '\n')
    print(json.dumps({'passed': result['passed'], 'error': result.get('error'),
                      'checks': len(result['checks']), 'review': str(destination)}, ensure_ascii=False))
    raise SystemExit(0 if result['passed'] else 1)


if __name__ == '__main__':
    main()
