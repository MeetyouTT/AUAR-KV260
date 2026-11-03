#!/usr/bin/env python3
"""Exercise report rejection gates using actual archived implementation reports."""
import json
from pathlib import Path
import re
import shutil
import tempfile

from finalize_offline import verify_reports

ROOT = Path(__file__).resolve().parent
PARENT = Path('/home/ghmd/kv260-visual-servo-20261007')


def main():
    audit = json.loads((PARENT / 'CURRENT_SOURCE_FINAL_AUDIT.json').read_text())
    fixture = Path(audit['evidence'])
    names = ['timing.rpt', 'route.rpt', 'drc.rpt', 'bus_skew.rpt', 'check_timing.rpt', 'pwm_timing.rpt']
    checked = []
    with tempfile.TemporaryDirectory(prefix='aura-pan-report-gates-') as name:
        directory = Path(name)

        def reset():
            for n in names:
                shutil.copy2(fixture / n, directory / n)

        reset()
        verify_reports(directory)
        checked.append('valid_archived_reports_accept')

        def rejected(label, filename, transform):
            reset()
            path = directory / filename
            before = path.read_text()
            after = transform(before)
            if before == after:
                raise RuntimeError('Fault injection did not change ' + filename)
            path.write_text(after)
            try:
                verify_reports(directory)
            except RuntimeError:
                checked.append(label)
            else:
                raise RuntimeError('Invalid reports accepted: ' + label)

        def negative_setup(text):
            match = re.search(r'(WNS\(ns\).*?\n\s*[- ]+\n\s*)([^\n]+)', text, re.S)
            row = match[2].split()
            row[0] = '-0.001'
            return text[:match.start(2)] + ' '.join(row) + text[match.end(2):]

        rejected('negative_setup_reject', 'timing.rpt', negative_setup)
        rejected('unrouted_net_reject', 'route.rpt',
                 lambda s: re.sub(r'(# of nets with routing errors\.*\s*:\s*)0', r'\g<1>1', s))
        rejected('drc_error_reject', 'drc.rpt', lambda s: s.replace('| Warning', '| Error', 1))
        rejected('bus_skew_violation_reject', 'bus_skew.rpt', lambda s: s.replace('(MET)', '(VIOLATED)', 1))
        rejected('unconstrained_internal_reject', 'check_timing.rpt',
                 lambda s: s.replace('checking unconstrained_internal_endpoints (0)', 'checking unconstrained_internal_endpoints (1)', 1))
        rejected('wrong_pwm_path_reject', 'pwm_timing.rpt', lambda s: s.replace('servo_pwm_reg/C', 'other_reg/C'))
        rejected('empty_timing_reject', 'timing.rpt', lambda s: '')
    result = {'passed': True, 'checks': checked, 'count': len(checked),
              'board_accessed': False, 'new_implementation_audited': False,
              'fixture': str(fixture)}
    (ROOT / 'release-gate-tests.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
