#!/usr/bin/env python3
"""Summarize complete UART action evidence and new monotonic kernel messages."""
import json
from pathlib import Path
import re
import sys


def main():
    run = Path(sys.argv[1])
    phase = sys.argv[2]
    rows = [json.loads(line) for line in (run / (phase + '.results.jsonl')).read_text().splitlines()]
    commands = [r for r in rows if r.get('type') == 'command']
    review = {'phase': phase, 'all_commands_complete_and_successful': bool(commands) and all(r['complete'] and r['exit_code'] == 0 for r in commands), 'commands': []}
    for row in commands:
        output = row.get('output') or ''
        before = re.search(r'^BEFORE_UPTIME ([0-9.]+)', output, re.M)
        after = re.search(r'^AFTER_UPTIME ([0-9.]+)', output, re.M)
        kernel = re.search(r'^AFTER_DMESG_BEGIN\n(.*?)^AFTER_DMESG_END', output, re.M | re.S)
        lines = kernel[1].splitlines() if kernel else []
        start = float(before[1]) if before else (float(sys.argv[3]) if len(sys.argv) > 3 else None)
        end = float(after[1]) if after else None
        fresh = []
        for line in lines:
            match = re.match(r'^\[\s*([0-9.]+)\]', line)
            if match and (start is None or float(match[1]) >= start):
                fresh.append(line)
        entry = {'id': row['id'], 'returncode': row['exit_code'], 'integrity_sha256': row.get('integrity_sha256'),
                 'uptime_before': start, 'uptime_after': end, 'kernel_interval_isolated': start is not None,
                 'start_source': 'this_stage_BEFORE' if before else ('explicit_prior_snapshot' if start is not None else 'not_isolated'),
                 'new_kernel_lines': fresh,
                 'refcount_errors': [line for line in fresh if 'expected refcount' in line],
                 'property_warnings': [line for line in fresh if 'memory leak will occur' in line],
                 'exception_lines': [line for line in fresh if re.search(r'BUG:|Oops:|Unable to handle|Kernel panic|Call trace:', line)],
                 'other_error_lines': [line for line in fresh if re.search(r'ERROR|error|\*ERROR\*', line) and 'expected refcount' not in line]}
        review['commands'].append(entry)
    path = run / (phase + '.review.json')
    if path.exists():
        raise RuntimeError('Refusing to overwrite phase review')
    path.write_text(json.dumps(review, indent=2, ensure_ascii=False) + '\n')
    print(json.dumps({'phase': phase, 'complete_success': review['all_commands_complete_and_successful'],
        'commands': [{k: e[k] for k in ('id', 'uptime_before', 'uptime_after', 'kernel_interval_isolated', 'refcount_errors', 'exception_lines', 'other_error_lines')} for e in review['commands']]}, ensure_ascii=False))


if __name__ == '__main__':
    main()
