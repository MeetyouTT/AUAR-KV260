#!/usr/bin/env python3
"""Check the generated VSRV/2 source handoff without accessing hardware."""
import hashlib
import importlib.util
import json
from pathlib import Path
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parent
PARENT = Path('/home/ghmd/kv260-visual-servo-20261007')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    base = ROOT / 'platform'
    bd, = (base / 'platform/platform.srcs').rglob('*.bd')
    hwh, = (base / 'platform/platform.gen').rglob('kv260_ispMipiRx_vcu_DP.hwh')
    old = json.loads((base / 'inputs/bd/kv260_ispMipiRx_vcu_DP.bd').read_text())['design']
    new = json.loads(bd.read_text())['design']
    spec = importlib.util.spec_from_file_location('historic_audit', PARENT / 'scripts/audit_source_platform.py')
    helper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helper)
    changes = helper.component_diff(old['components'], new['components'])
    xml = ET.parse(hwh).getroot()
    modules = {m.get('INSTANCE'): m for m in xml.iter('MODULE')}
    motion = modules['aura_m3_regs_0']
    parameters = {p.get('NAME'): p.get('VALUE') for p in motion.iter('PARAMETER')}
    clock = motion.find("./PORTS/PORT[@NAME='s_axi_aclk']")
    reset = motion.find("./PORTS/PORT[@NAME='s_axi_aresetn']")
    ranges = [m.attrib for m in xml.iter('MEMRANGE') if m.get('INSTANCE') == 'aura_m3_regs_0']
    old_nets = {frozenset(v['ports']) for v in old['nets'].values()}
    old_nets.discard(frozenset(('audio_ss_0/lrclk_tx', 'lrclk_tx')))
    expected_nets = old_nets | {frozenset(('aura_m3_regs_0/servo_pwm', 'servo_pwm'))}
    actual_nets = {frozenset(v['ports']) for v in new['nets'].values() if v.get('ports')}
    checks = {
        'build_id': int(parameters['BUILD_ID'], 0) == 0x10282601,
        'wide_range_parameters': all(int(parameters[k],0)==v for k,v in {'MIN_US':500,'MAX_US':2500,'CENTER_US':1500,'STEP_US':4}.items()),
        'bd_pwm_output': new['ports'].get('servo_pwm', {}).get('direction') == 'O' and 'lrclk_tx' not in new['ports'],
        'hwh_pwm_output': any(p.get('NAME') == 'servo_pwm' for p in xml.findall('./EXTERNALPORTS/PORT')),
        'motion_pwm_output': motion.find("./PORTS/PORT[@NAME='servo_pwm']") is not None,
        'motion_100mhz': clock is not None and clock.get('SIGNAME') == 'clk_wiz_0_clk_100M'
            and 99990000 <= int(clock.get('CLKFREQUENCY', '0')) <= 100010000,
        'motion_reset': reset is not None and reset.get('POLARITY') == 'ACTIVE_LOW'
            and any(c.get('INSTANCE') == 'proc_sys_reset_100MHz' and c.get('PORT') == 'peripheral_aresetn'
                    for c in reset.findall('./CONNECTIONS/CONNECTION')),
        'motion_address': any(int(r['BASEVALUE'], 0) == 0x80080000 and int(r['HIGHVALUE'], 0) == 0x80080fff for r in ranges),
        'other_components_preserved': not changes,
        'scalar_connections': actual_nets == expected_nets,
        'axi_connections': {frozenset(v['interface_ports']) for v in old['interface_nets'].values()}
            == {frozenset(v['interface_ports']) for v in new['interface_nets'].values()},
        'disabled_audio_stub': new['components']['audio_ss_0']['vlnv'] == 'aura.local:user:aura_disabled_audio:1.0',
        'legacy_audio_removed': not any(n.startswith('audio_ss_0_') and not n.endswith('_stub') for n in modules),
        'packaged_rtl_exact': sha(base / 'ip_repo/aura_visual_servo/src/visual_servo.sv')
            == sha(ROOT / 'candidate/rtl/visual_servo.sv'),
    }
    result = {'passed': all(checks.values()), 'checks': checks, 'build_id': '0x10282601', 'abi': 2,
              'board_accessed': False, 'deployable': False, 'retained_component_changes': changes,
              'generated_bd': str(bd), 'generated_hwh': str(hwh),
              'source_sha256': {str(p): sha(p) for p in [bd, hwh, base / 'pin.xdc', Path(__file__)]}}
    (ROOT / 'handoff-audit.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))
    return 0 if result['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
