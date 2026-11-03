"""Execute one reviewed public ARM probe in the root's exclusive window."""
import argparse
import datetime
import hashlib
import json
from pathlib import Path
import sys
import time

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parents[2]
sys.path.insert(0, str(PROJECT/'deliverables/2026-10-18_board_dialogue'))
from board_ssh import ssh
from resume_baseline import write_json


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('kind', choices=('audio', 'clock', 'retention', 'text', 'factory'))
    parser.add_argument('--num-threads', type=int, choices=(1, 2), default=1)
    parser.add_argument('--audio-mode', choices=('pipeline', 'frontend-profile'), default='pipeline')
    parser.add_argument('--runs', type=int, choices=(1, 2, 3), default=1)
    parser.add_argument('--process-nice', type=int, choices=(0, -5, -10), default=0)
    args = parser.parse_args()
    window = json.loads((HERE.parent/'coordination/runtime_windows.json').read_text(encoding='utf-8-sig'))
    if window['performance_window'].get('state') != 'BUSINESS_ACCEPTANCE_EXCLUSIVE':
        raise RuntimeError('Root no longer owns the resource window')
    staged = json.loads((HERE/'resume_bundle/staged.json').read_text(encoding='utf-8'))
    candidate = staged['candidate_root']
    if not candidate.startswith('/home/root/aura-board-owner-candidate-20261030/resume-'):
        raise RuntimeError('Unexpected candidate directory')
    now = datetime.datetime.now(datetime.timezone.utc)
    if args.kind == 'audio':
        source = HERE/'resume_inference/board_audio_pipeline_probe.py'
        arguments = ['--code-root', candidate+'/code', '--resources-root', '/home/root/aura-board-owner-candidate-20261030']
        arguments += ['--num-threads', str(args.num_threads), '--mode', args.audio_mode, '--runs', str(args.runs)]
        arguments += ['--process-nice', str(args.process_nice)]
        timeout = 110
    elif args.kind == 'factory':
        source = HERE/'resume_runtime/posix_factory_smoke.py'
        arguments = ['--aura-root', candidate+'/code']
        timeout = 30
    else:
        source = HERE/({'clock':'resume_clock_check.py', 'retention':'resume_retention_check.py',
                       'text':'resume_model_chain_check.py'}[args.kind])
        arguments = ['--candidate-root', candidate, '--utc-min', str(now.timestamp()-86400),
                     '--utc-max', str(now.timestamp()+86400)]
        timeout = {'clock':30, 'text':85, 'retention':395}[args.kind]
    payload = source.read_text(encoding='utf-8')
    compile(payload, str(source), 'exec')
    prefix = 'import sys\nsys.argv=' + repr([source.name]+arguments) + '\n'
    result = dict(kind=args.kind, began_utc=now.isoformat(), source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
                  staged_fingerprint=staged['source_fingerprint'], production_entry_changed=False)
    began = time.monotonic()
    try:
        raw = ssh('python3 -B -', prefix+payload, timeout=timeout)
        value = json.loads(raw)
        result.update(status=value.get('status', 'PROBE_RETURNED'), result=value)
    except Exception as error:
        result.update(status='ERROR', error_type=type(error).__name__, error=str(error)[-6000:])
        try:
            diagnostic = json.loads(str(error))
            if isinstance(diagnostic, dict):
                result.update(status=diagnostic.get('status', 'ERROR'), result=diagnostic)
        except (ValueError, TypeError):
            pass
    result['elapsed_seconds'] = round(time.monotonic()-began, 3)
    path = HERE/'resume_actual'/(now.strftime('%Y%m%dT%H%M%S')+'-'+args.kind+'.json')
    write_json(path, result)
    write_json(HERE/'resume_actual'/('latest-'+args.kind+'.json'), result)
    display = dict(output=str(path), kind=args.kind, status=result['status'], elapsed_seconds=result['elapsed_seconds'])
    value = result.get('result', {})
    if 'runs' in value:
        display.update(num_threads=value.get('num_threads'), runs=[dict(run=row['run'],
            processing_rtf=row['processing_rtf'], processing_ms=row['frontend_processing_ms'],
            decision_sha256=row['decision_sha256']) for row in value['runs']])
    else:
        display.update(result=value if value else result.get('error', ''))
    print(json.dumps(display, ensure_ascii=True))
    raise SystemExit(0 if result['status'] in ('PASS', 'DIAGNOSTIC_FRONTEND_PROFILE_ONLY') else 1)


if __name__ == '__main__':
    main()
