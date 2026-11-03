"""Bounded, read-only metadata observation; no audio or transcript export."""
import argparse
import json
import sys
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / '2026-10-18_board_dialogue'))
from board_ssh import ssh

REMOTE = r'''
import json, subprocess, time, urllib.request
unit = subprocess.check_output(
    ['systemctl', 'show', 'aura-avatar-ui.service', '-p', 'MainPID',
     '-p', 'ExecStart', '-p', 'ActiveState'], text=True)
rows = []
deadline = time.monotonic() + DURATION
while True:
    at = time.monotonic()
    try:
        with urllib.request.urlopen('http://127.0.0.1:8783/api/state', timeout=3) as response:
            u = json.load(response)
        h = u.get('handsfree_dialogue', {})
        b = u.get('voice_barge_in', {})
        tx = u.get('local_transcription', {})
        rows.append({
            'board_monotonic': at, 'ok': True,
            'handsfree': {k: h.get(k) for k in (
                'enabled', 'state', 'reason', 'microphone_open',
                'conversation_entered', 'listening_timing', 'diagnostics')},
            'barge_in': {k: b.get(k) for k in (
                'enabled', 'listening', 'interrupted_turns',
                'continuation_handoffs', 'next_utterance_pending',
                'last_detection_to_stop_ms')},
            'barge_error_present': bool(b.get('error')),
            'ui_error_present': bool(u.get('error')),
            'transcription_error_present': bool(tx.get('error')),
            'transcription_state': tx.get('state'),
            'recording_state': u.get('local_recording', {}).get('state'),
            'phase': u.get('phase'), 'playing': u.get('playing'),
            'audio_output_state': u.get('audio_output_state'),
            'completed_turns': u.get('automatic_conversation', {}).get('completed_turns'),
            'playback_ack_present': bool(tx.get('service', {}).get('last_playback_ack')),
        })
    except Exception as exc:
        rows.append({'board_monotonic': at, 'ok': False,
                     'error_type': type(exc).__name__})
    remaining = deadline - time.monotonic()
    if remaining <= 0:
        break
    time.sleep(min(5, remaining))
print(json.dumps({'unit': unit, 'rows': rows}))
'''


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--seconds', type=int, default=1800)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    if not 5 <= args.seconds <= 3600:
        parser.error('seconds must be between 5 and 3600')
    args.out.mkdir(parents=True, exist_ok=False)
    started = time.monotonic()
    started_utc = datetime.now(timezone.utc).isoformat()
    batches = []
    failures = 0

    def save(status):
        rows = [row for batch in batches for row in batch['rows']]
        valid = [row for row in rows if row.get('ok')]
        units = list(dict.fromkeys(batch['unit'] for batch in batches))
        summary = {
            'status': status, 'started_utc': started_utc,
            'elapsed_seconds': round(time.monotonic() - started, 2),
            'requested_seconds': args.seconds, 'samples': len(rows),
            'valid_samples': len(valid), 'transport_failures': failures,
            'sample_failures': len(rows) - len(valid), 'units': units,
            'service_segments': len(units),
            'phase_samples': dict(Counter(row.get('phase') for row in valid)),
            'handsfree_state_samples': dict(Counter(
                row['handsfree'].get('state') for row in valid)),
            'ui_error_samples': sum(row['ui_error_present'] for row in valid),
            'barge_error_samples': sum(row['barge_error_present'] for row in valid),
            'transcription_error_samples': sum(row['transcription_error_present'] for row in valid),
            'first': valid[0] if valid else None,
            'latest': valid[-1] if valid else None,
            'human_verified': False, 'long_duration_verified': False,
            'audio_or_transcript_exported': False,
            'monitor_or_services_changed': False,
            'scope': 'State sampling alone does not prove audible answers or context correctness. Counter resets require segmented analysis.',
        }
        temporary = args.out / 'progress.tmp'
        temporary.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        temporary.replace(args.out / 'progress.json')

    save('OBSERVING_WAITING_HUMAN_RESULT')
    try:
        with (args.out / 'samples.jsonl').open('x', encoding='utf-8') as output:
            while time.monotonic() - started < args.seconds:
                if (args.out / 'STOP').exists():
                    save('STOPPED_BEFORE_COMPLETION')
                    return
                remaining = args.seconds - (time.monotonic() - started)
                duration = min(10 if not batches else 45, remaining)
                try:
                    result = json.loads(ssh('python3 -B -',
                        REMOTE.replace('DURATION', repr(duration), 1),
                        timeout=duration + 15))
                    result['client_elapsed_seconds'] = round(time.monotonic() - started, 2)
                    batches.append(result)
                    output.write(json.dumps(result, ensure_ascii=False) + '\n')
                    output.flush()
                except Exception as exc:
                    failures += 1
                    output.write(json.dumps({'transport_error_type': type(exc).__name__,
                        'client_elapsed_seconds': round(time.monotonic() - started, 2)}) + '\n')
                    output.flush()
                    time.sleep(min(5, max(0, args.seconds - (time.monotonic() - started))))
                save('OBSERVING_WAITING_HUMAN_RESULT')
        save('OBSERVATION_FINISHED_WAITING_HUMAN_RESULT')
    except BaseException:
        save('OBSERVER_STOPPED_WITH_ERROR')
        raise


if __name__ == '__main__':
    main()
