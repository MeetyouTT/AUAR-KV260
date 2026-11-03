#!/usr/bin/env python3
"""Run only the frozen reversible manager validation; stop on unexpected errors."""
import datetime
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OLD = Path('/home/ghmd/kv260-m3-boardtest-20261002/evidence/20261003T021012Z')


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def evidence(run, phase):
    rows = [json.loads(line) for line in (run / (phase + '.results.jsonl')).read_text().splitlines()]
    assert any(r.get('type') == 'connection' and r['ready'] for r in rows)
    commands = [r for r in rows if r.get('type') == 'command']
    expected = json.loads((run / (phase + '.commands.json')).read_text())
    assert [r['command'] for r in commands] == [r['command'] for r in expected]
    assert [r['id'] for r in commands] == [r['id'] for r in expected]
    for row in commands:
        assert row['complete'] and row['exit_code'] == 0
        assert sha(run / (phase + '.' + row['id'] + '.output')) == row['integrity_sha256']
    return commands


def record(text, prefix):
    match = re.search(r'^' + prefix + r' (.*)$', text, re.M)
    assert match, prefix + ' not found'
    return json.loads(match[1])


def top5(path):
    return re.findall(r'r[.]index +([0-9]+).*r[.]score +([0-9.eE+-]+)', path.read_text())


def main():
    run = Path(sys.argv[1]).resolve()
    assert not (run / 'controller.started.json').exists(), 'No automatic restart of board mutations'
    prepared = json.loads((run / 'preparation.json').read_text())
    for key in ('manifest_hashes', 'source_hashes'):
        for name, digest in prepared[key].items(): assert sha(run / name) == digest
    assert sha(run / 'collect_serial.py') == prepared['collector_sha256']
    assert sha(run / 'transfer_candidate.py') == prepared['transfer_sha256']
    assert sha(prepared['test_archive']['path']) == prepared['test_archive']['sha256']
    status = {'started_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
              'runner_sha256': sha(__file__), 'completed_phases': [], 'passed': False,
              'successful_commands': 0, 'kernel_reviews': []}
    (run / 'controller.started.json').write_text(json.dumps(status, indent=2) + '\n')
    expected_top5 = top5(OLD / '24-restored-functional.classification.output')
    assert len(expected_top5) == 5
    preflight = Path((ROOT / 'evidence/BOARD_PREFLIGHT_RUN').read_text().strip())
    epoch = float(json.loads((preflight / '01-readonly.identity_manager.output').read_text())['uptime'].split()[0])
    try:
        for phase in prepared['ordered_phases']:
            print('START FROZEN PHASE', phase, flush=True)
            if phase == '03-transfer':
                subprocess.run([sys.executable, str(run / 'transfer_candidate.py')], check=True)
                result = json.loads((run / '03-transfer.result.json').read_text())
                assert result['complete'] and result['expected_sha256'] == prepared['test_archive']['sha256']
                status['transfer'] = {k: result[k] for k in ('bytes', 'expected_sha256', 'frames_acknowledged', 'complete')}
                commands = []
            else:
                subprocess.run([sys.executable, str(run / 'collect_serial.py'), phase], check=True)
                commands = evidence(run, phase)
            status['successful_commands'] += len(commands)
            if any('BEFORE_DMESG_BEGIN\n' in (r.get('output') or '') for r in commands):
                subprocess.run([sys.executable, str(ROOT / 'scripts/review_board_phase.py'), str(run), phase, str(epoch)], check=True)
                review = json.loads((run / (phase + '.review.json')).read_text())
                for row in review['commands']:
                    assert row['kernel_interval_isolated']
                    assert not row['exception_lines'] and not row['other_error_lines'], 'Unexpected kernel diagnostic'
                    if phase == '05-remove-original':
                        assert len(row['refcount_errors']) <= 1
                        assert all('/axi/zyxclmm_drm' in s and 'expected refcount 1 instead of 2' in s for s in row['refcount_errors'])
                    else:
                        assert not row['refcount_errors'], 'New reference error after the validated driver'
                    epoch = row['uptime_after']
                status['kernel_reviews'].append({'phase': phase, 'review': str((run / (phase + '.review.json')).relative_to(ROOT))})
            if phase == '02-backup':
                backup = record((run / '02-backup.backup.output').read_text(), 'BACKUP')
                assert all(prepared['input_hashes'][p] == h for p, h in backup['files'].items())
                status['baseline_backup'] = backup
            if 'functional' in phase or phase == '11-official-after-cycles':
                query = json.loads((run / (phase + '.dpu_query.output')).read_text())
                assert query['DPU IP Spec']['DPU Core Count'] == 1 and len(query['kernels']) == 1
                kernel = query['kernels'][0]
                assert kernel['fingerprint'] == '0x101000056010407'
                assert kernel['DPU Arch'] == 'DPUCZDX8G_ISA1_B4096' and kernel['cu_addr'] == '0xa0010000'
                assert kernel['DPU Frequency (MHz)'] == 300 and kernel['XRT Frequency (MHz)'] == 300
                assert query['DPU IP Spec']['git commit id'] == ('7d32c41' if phase == '13-m3-functional' else 'ce8dd1')
                assert top5(run / (phase + '.classification.output')) == expected_top5
                status.setdefault('functional', []).append({'phase': phase, 'top5_match': True, 'dpu_match': True})
            if phase == '08-query-stress':
                test = record((run / '08-query-stress.queries.output').read_text(), 'QUERY_STRESS')
                assert test['queries'] == 1000 and len(test['samples']) == 6
                assert all(s['watches'] == 5 for s in test['samples']) and not test['manager_errors']
                status['query_stress'] = test
            if phase == '09-directory-stress':
                test = record((run / '09-directory-stress.directories.output').read_text(), 'DIRECTORY_STRESS')
                assert test['cycles'] == 50 and test['probe_absent'] and test['kernel_watches'] == 5
                assert not test['manager_errors']
                status['directory_stress'] = test
            if phase == '10-official-cycles':
                text = (run / '10-official-cycles.cycles.output').read_text()
                cycles = [json.loads(s) for s in re.findall(r'^OFFICIAL_CYCLE (.*)$', text, re.M)]
                assert len(cycles) == 3 and all(c['watches'] == 5 for c in cycles)
                status['official_cycles'] = cycles
            if phase == '17-final-state':
                final = record((run / '17-final-state.state.output').read_text(), 'FINAL')
                assert final['boot_id'] == prepared['boot_id'] and final['original_files'] == prepared['input_hashes']
                assert final['driver'] == '0991D1B457855C8987936E6' and final['parameters'] == {'enable_xgq_ert': '1'}
                assert final['active'] == [['kv260-benchmark-b4096', 0]]
                assert final['manager_exe'] == '/usr/bin/dfx-mgrd'
                status['original_baseline_restored'] = True
                status['final'] = final
            if phase == '18-candidate-log':
                log = run / '18-candidate-log.log.output'
                assert sha(log) == status['final']['candidate_log_sha256']
                assert log.stat().st_size == status['final']['candidate_log_bytes']
                errors = [s for s in log.read_text(errors='replace').splitlines() if 'ERROR:' in s]
                assert not errors
                status['candidate_error_lines'] = errors
                status['candidate_log_sha256'] = sha(log)
            status['completed_phases'].append(phase)
            (run / 'controller.progress.json').write_text(json.dumps(status, indent=2) + '\n')
            print('PHASE EVIDENCE PASSED', phase, flush=True)
        status['passed'] = True
        status['board_verified'] = True
        print('FINITE MANAGER VALIDATION AND ORIGINAL BASELINE RECOVERY FINISHED', flush=True)
    except Exception as error:
        status['error'] = str(error)
        print('STOPPED WITHOUT RETRY:', str(error), flush=True)
    finally:
        status['finished_utc'] = datetime.datetime.now(datetime.timezone.utc).isoformat()
        (run / 'controller.result.json').write_text(json.dumps(status, indent=2) + '\n')
    return 0 if status['passed'] else 1


if __name__ == '__main__':
    sys.exit(main())
