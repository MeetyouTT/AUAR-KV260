#!/usr/bin/env python3
"""Check intended connector pin against XDC and the existing routed IO report."""
import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]


def audit():
    preparation = json.loads((ROOT / 'PREPARATION_STATUS.json').read_text())
    physical = json.loads((ROOT / 'PHYSICAL_CONNECTION.json').read_text())
    mapping = json.loads((ROOT / 'J2_PIN_MAP.json').read_text())['signal_pins']
    intended = preparation['intended_physical_pin']
    expected = mapping[intended]['fpga_pin']
    xdc_path = ROOT / 'constraints/j2.xdc'
    xdc_pins = re.findall(
        r'^set_property PACKAGE_PIN (\w+) \[get_ports servo_pwm\]$',
        xdc_path.read_text(), re.M)
    build = json.loads((ROOT / 'CURRENT_BUILD.json').read_text())
    evidence = Path(build['evidence'])
    built_pins = re.findall(r'^\|\s+(\w+)\s+\|\s+servo_pwm\s+\|',
                            (evidence / 'io.rpt').read_text(), re.M)
    identity = json.loads((evidence / 'source_identity.json').read_text())
    source_matches_build = hashlib.sha256(xdc_path.read_bytes()).hexdigest() == \
        identity['inputs'][str(xdc_path)]
    compiled = built_pins[0] if len(built_pins) == 1 else None
    actual_pins = [pin for pin, row in mapping.items()
                   if row['fpga_pin'] == compiled]
    passed = (source_matches_build and xdc_pins == [expected] and
              built_pins == [expected])
    connection_eligible = (physical.get('pin') == intended and
                           physical.get('confirmed') is True and
                           (physical.get('connection') in ('empty', 'measurement_only') or
                            (physical.get('connection') == 'servo_via_signal_isolator_and_SVPDB_8S' and
                             physical.get('isolator_VIB_actual_KV260_pin') == intended and
                             physical.get('appropriate_servo_supply_confirmed_by_user') is True)))
    return {
        'passed': passed,
        'intended_physical_pin': intended,
        'expected_fpga_pin': expected,
        'xdc_fpga_pins': xdc_pins,
        'built_fpga_pins': built_pins,
        'actual_physical_pins': actual_pins,
        'constraint_identity_unchanged': source_matches_build,
        'build_evidence': str(evidence),
        'board_accessed': bool(preparation.get('board_accessed', False)),
        'pl_loaded': bool(preparation.get('pl_loaded', False)),
        'external_connection_confirmed': connection_eligible,
        'deployment_allowed': passed and preparation['ready_for_upload'] and connection_eligible
    }


if __name__ == '__main__':
    report = audit()
    (ROOT / 'PIN_MAPPING_REVIEW.json').write_text(
        json.dumps(report, indent=2) + '\n')
    print(json.dumps(report))
    raise SystemExit(0 if report['passed'] else 1)
