#!/usr/bin/env python3
"""Collect completed host build evidence without changing hardware artifacts."""
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import subprocess
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parent
BENCH = ROOT / 'src/kv260/overlays/examples/benchmark'
BUILD = BENCH / 'binary_container_1'
SD = BUILD / 'sd_card'
POST = ROOT / 'evidence/postroute'


def sha(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def write_json(name, data):
    (ROOT / 'evidence' / name).write_text(json.dumps(data, indent=2, ensure_ascii=False) + '\n')


def artifacts():
    selected = [
        ('reused_platform', ROOT / 'platform/kv260_ispMipiRx_vcu_DP.xpfm'),
        ('reused_platform', ROOT / 'platform/hw/kv260_ispMipiRx_vcu_DP.xsa'),
        ('reused_platform', ROOT / 'platform/sw/kv260_ispMipiRx_vcu_DP.spfm'),
        ('new_xo', BUILD / 'dpu.xo'),
        ('new_metadata_xclbin', SD / 'dpu.xclbin'),
        ('new_bit', SD / 'kv260_ispMipiRx_vcu_DP_wrapper.bit'),
        ('new_hwh', SD / 'kv260_ispMipiRx_vcu_DP.hwh'),
        ('new_arch', SD / 'arch.json'),
        ('new_bootgen_full_bin', ROOT / 'test_bundle/provenance/candidate-full-bootgen.bin'),
        ('new_routed_dcp', BUILD / 'link/vivado/vpl/prj/prj.runs/impl_1/kv260_ispMipiRx_vcu_DP_wrapper_routed.dcp'),
    ]
    selected.extend(('new_link_export_xsa', p) for p in BUILD.rglob('*.xsa'))
    selected.extend(('prepared_runtime_file', p) for p in (ROOT / 'test_bundle/lib/firmware/xilinx').rglob('*') if p.is_file())
    records = []
    for role, path in selected:
        assert path.is_file(), path
        records.append({'role': role, 'path': path.relative_to(ROOT).as_posix(), 'bytes': path.stat().st_size, 'sha256': sha(path)})
    write_json('artifacts.json', records)
    (ROOT / 'evidence/ARTIFACTS.sha256').write_text(''.join(item['sha256'] + '  ' + item['path'] + '\n' for item in records))
    return records


def compatibility():
    hwh = ET.parse(SD / 'kv260_ispMipiRx_vcu_DP.hwh')
    modules = [m for m in hwh.iter('MODULE') if m.get('INSTANCE') == 'DPUCZDX8G_1']
    assert len(modules) == 1
    props = {p.get('NAME'): p.get('VALUE') for p in modules[0].findall('./PARAMETERS/PARAMETER')}
    assert int(props['SYS_IP_VER'], 0) == 0x41
    assert props['SAVE_ARGMAX_ENA'] == '1'
    assert int(props['C_BASEADDR'], 0) == 0xa0010000
    assert int(props['C_HIGHADDR'], 0) == 0xa0010fff
    arch = json.loads((SD / 'arch.json').read_text())
    assert int(arch['fingerprint'], 0) == 0x101000056010407
    layout = json.loads((ROOT / 'evidence/xclbin_IP_LAYOUT.json').read_text())['ip_layout']
    cus = layout['m_ip_data']
    assert len(cus) == 1
    assert cus[0]['m_name'] == 'DPUCZDX8G:DPUCZDX8G_1'
    assert int(cus[0]['m_base_address'], 0) == 0xa0010000
    connectivity = json.loads((ROOT / 'evidence/xclbin_CONNECTIVITY.json').read_text())['connectivity']['m_connection']
    original_connectivity = json.loads((ROOT / 'evidence/original_xclbin_CONNECTIVITY.json').read_text())['connectivity']['m_connection']
    info = (ROOT / 'evidence/xclbin_info.log').read_text()
    uuid = re.search(r'UUID \(xclbin\):\s*([0-9a-f-]{36})', info)
    assert uuid, 'XCLBIN UUID not found in xclbinutil info'
    clocks = {name.strip(): float(freq) for name, freq in re.findall(
        r'Name:\s*(clk_wiz_0_clk_\d+M)\s*\n\s*Type:\s*FIXED\s*\n\s*Default Freq:\s*([\d.]+) MHz', info)}
    assert set(clocks) == {'clk_wiz_0_clk_100M', 'clk_wiz_0_clk_300M', 'clk_wiz_0_clk_600M'}
    clock_expected = {'clk_wiz_0_clk_100M': 100, 'clk_wiz_0_clk_300M': 300, 'clk_wiz_0_clk_600M': 600}
    clock_match = all(abs(clocks[name] - expected) < 1 for name, expected in clock_expected.items())
    result = {
        'status': 'PASS host metadata; actual board registers and inference NOT RUN',
        'arch': arch,
        'model_required_fingerprint': '0x101000056010407',
        'baseline_resnet18_sha256': '4d4d669c84b6d5aa6f731b389ebcf0f51fb1449752cf5fa4a4beddd496c3c0ef',
        'hwh_module': modules[0].attrib,
        'hwh_parameters': props,
        'xclbin_cus': cus,
        'xclbin_connectivity': connectivity,
        'connectivity_matches_original_reference': connectivity == original_connectivity,
        'xclbin_uuid': uuid.group(1),
        'system_clocks_mhz': clocks,
        'requested_clock_match_within_1mhz': clock_match,
        'baseline_runtime': {'petalinux': '2022.2', 'xrt_zocl': '202220.2.14.0', 'vart': '3.0'},
        'board_load_test': 'NOT RUN',
    }
    write_json('compatibility_validation.json', result)


def drc():
    report = (POST / 'drc.rpt').read_text()
    details = re.findall(r'^([A-Z]+-\d+)#\d+\s+(Critical Warning|Warning|Error|Info)\s*$', report, re.MULTILINE)
    counts = Counter(details)
    found = int(re.search(r'Violations found:\s*(\d+)', report).group(1))
    assert found == len(details), (found, len(details))
    records = [{'check': check, 'severity': severity, 'count': count} for (check, severity), count in sorted(counts.items())]
    write_json('drc_summary.json', {'total': found, 'severity_counts': dict(Counter(sev for _, sev in details)), 'rules': records, 'actual_HDPR_5_count': sum(n for (c, _), n in counts.items() if c == 'HDPR-5'), 'report': 'evidence/postroute/drc.rpt'})
    (POST / 'drc_rule_summary.tsv').write_text('CHECK\tSEVERITY\tCOUNT\n' + ''.join(f"{x['check']}\t{x['severity']}\t{x['count']}\n" for x in records))


def timing_and_resources():
    timing = (POST / 'timing_summary.rpt').read_text()
    lines = timing.splitlines()
    heading = next(i for i, line in enumerate(lines) if 'WNS(ns)' in line and 'WHS(ns)' in line and 'WPWS(ns)' in line)
    values = lines[heading + 2].split()
    assert len(values) == 12, values
    keys = ['wns_ns', 'tns_ns', 'setup_failing_endpoints', 'setup_total_endpoints',
            'whs_ns', 'ths_ns', 'hold_failing_endpoints', 'hold_total_endpoints',
            'wpws_ns', 'tpws_ns', 'pulse_failing_endpoints', 'pulse_total_endpoints']
    numbers = {key: float(value) if key.endswith('_ns') else int(value)
               for key, value in zip(keys, values)}
    check = (POST / 'check_timing.rpt').read_text()
    checks = {name: int(count) for name, count in re.findall(
        r'^\d+\. checking ([a-z_]+) \((\d+)\)', check, re.MULTILINE)}
    assert checks['unconstrained_internal_endpoints'] >= 0
    result = {'summary': numbers, 'check_timing_counts': checks,
              'all_setup_hold_pulse_endpoints_meet_timing': all(numbers[key] == 0 for key in
                ['setup_failing_endpoints', 'hold_failing_endpoints', 'pulse_failing_endpoints']),
              'complete_io_delay_coverage': checks['no_input_delay'] == 0 and checks['no_output_delay'] == 0,
              'report_files': ['evidence/postroute/timing_summary.rpt', 'evidence/postroute/check_timing.rpt']}
    write_json('timing_validation.json', result)

    utilization = (POST / 'utilization.rpt').read_text()
    resource_names = ['CLB LUTs', 'CLB Registers', 'CLB', 'Block RAM Tile', 'URAM', 'DSPs']
    resources = {}
    for line in utilization.splitlines():
        if not line.startswith('|'):
            continue
        fields = [x.strip() for x in line.strip('|').split('|')]
        if len(fields) < 6 or fields[0] not in resource_names:
            continue
        if not re.fullmatch(r'[\d.]+', fields[1]):
            continue
        resources[fields[0]] = {'used': float(fields[1]), 'available': float(fields[4]), 'percent': float(fields[5])}
    assert set(resources) == set(resource_names), resources
    inv = (POST / 'inventory.txt').read_text()
    pblock = re.search(r'^PBLOCK_COUNT=(\d+)', inv, re.MULTILINE)
    assert pblock
    write_json('resource_validation.json', {'resources': resources,
              'pblock_count': int(pblock.group(1)),
              'reconfigurable_cells': re.search(r'^RECONFIGURABLE_CELLS=(.*)$', inv, re.MULTILINE).group(1).strip(),
              'scope': 'actual routed design; flat static logic if zero Pblocks/reconfigurable cells',
              'report_files': ['evidence/postroute/utilization.rpt', 'evidence/postroute/utilization_hierarchical.rpt']})


def preserve_check():
    original = Path('/home/ghmd/kv260-reference-2022.2-20260930')
    code = subprocess.run(['git', '-C', str(original / 'src'), 'diff', '--exit-code'], capture_output=True, text=True)
    assert code.returncode == 0, 'Original tracked source changed'
    copied = []
    for target in (ROOT / 'platform').rglob('*'):
        if target.is_file():
            relative = target.relative_to(ROOT / 'platform')
            source = original / 'src/kv260/platforms/xilinx_kv260_ispMipiRx_vcu_DP_202220_1' / relative
            assert source.is_file(), source
            assert sha(target) == sha(source), relative
            copied.append(str(relative))
    write_json('original_preservation_check.json', {'original_source_tracked_diff': 'EMPTY', 'platform_copies_identical': copied, 'board_operations': 'NONE'})


if __name__ == '__main__':
    compatibility()
    drc()
    timing_and_resources()
    preserve_check()
    records = artifacts()
    print(f'Collected {len(records)} artifact records and verified host compatibility, DRC counts, original source/platform preservation')
