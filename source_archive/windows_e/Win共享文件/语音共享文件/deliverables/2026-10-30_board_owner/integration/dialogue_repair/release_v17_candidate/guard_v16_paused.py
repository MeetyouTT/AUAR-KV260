"""Root-only normal close wrapper for exact never-armed paused v16 state.

Default is source-only validation. Original publisher and spec stay unchanged.
"""
import argparse
import ast
import json
from pathlib import Path
import time
from release_common import (HERE, INTEGRATION, PUBLISH_SHA, create_json, frozen_v16_spec,
                            publisher_script, remote_from, replace_once, sha, ssh_json)

QUIET_HELPER = '''
def never_armed_paused_capture(v):
 h=v.get('handsfree_dialogue',{});d=v.get('safe_capture_diagnostics',{})
 recording=v.get('local_recording',{});task=v.get('local_transcription',{})
 faults=v.get('runtime_faults',{});dialogue=v.get('board_business',{}).get('dialogue',{})
 counters=d.get('counters',{})
 return (h.get('enabled') is False and h.get('state')=='PAUSED'
  and h.get('microphone_open') is False and h.get('conversation_entered') is False
  and d.get('snapshot_available') is False and d.get('capture_state')=='UNKNOWN'
  and d.get('monitor_enabled') is False and d.get('monitor_state')=='PAUSED'
  and d.get('recording_state')=='IDLE' and d.get('error_code')=='none'
  and d.get('error_source')=='none' and d.get('capture')=={}
  and d.get('input_queue')=={} and d.get('audio_frontend')=={}
  and type(counters.get('armed')) is int and counters['armed']==0
  and type(counters.get('speech_starts')) is int and counters['speech_starts']==0
  and type(counters.get('submitted')) is int and counters['submitted']==0
  and recording.get('state')=='IDLE' and recording.get('error')==''
  and recording.get('sample_count')==0 and recording.get('can_stop') is False
  and task.get('state')=='DISABLED' and task.get('error')==''
  and v.get('phase')=='IDLE' and v.get('playing') is False
  and v.get('audio_output_state')=='IDLE_READY' and v.get('error')==''
  and type(faults.get('count')) is int and faults['count']==0
  and faults.get('last') is None and dialogue.get('pending') is False
  and v.get('pending_job') is None and v.get('avatar_command_pending') in (None,False,0)
  and v.get('streaming_reply') in (None,False))
'''


def build_remote():
    original = remote_from('production_business_acceptance/publish_business_ui.py', PUBLISH_SHA)
    old = "quiet_capture=(d.get('capture',{}).get('speech_active') is False or\n     h.get('microphone_open') is False and d.get('capture_state') in ('IDLE','CANCELLED','CLOSED','ERROR'))"
    new = old[:-1] + " or\n     never_armed_paused_capture(v))"
    remote = replace_once(original, old, new)
    remote = replace_once(remote, '\ndef state():', QUIET_HELPER + '\ndef state():')
    remote = "assert ACTION in ('guard','window-inspect','normal-close')\n" + remote
    ast.parse(remote, feature_version=(3, 9))
    return remote


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('guard', 'window-inspect', 'normal-close'))
    parser.add_argument('--spec', type=Path, default=INTEGRATION/'production_business_acceptance/spec.json')
    parser.add_argument('--window-proof', type=Path)
    parser.add_argument('--execute-root-only', action='store_true')
    args = parser.parse_args()
    spec, remote = frozen_v16_spec(args.spec), build_remote()
    values = dict(SPEC=spec, ACTION=args.action, TOKEN=None, WINDOW=None)
    if args.action == 'normal-close':
        if args.window_proof is None:
            parser.error('--window-proof is required for exact normal close')
        checked = json.loads(args.window_proof.read_bytes())
        assert checked['status'] == 'WINDOW_INSPECTED_NO_CLOSE'
        values.update(TOKEN=checked['review_token'], WINDOW=checked['window']['window_id'])
    if not args.execute_root_only:
        print(json.dumps(dict(status='DRY_SOURCE_VALIDATED_NO_SSH', action=args.action,
                              remote_sha256=sha(remote.encode()), source_publisher_sha256=PUBLISH_SHA)))
        return
    result = ssh_json(publisher_script(remote, values), timeout=225)
    path = HERE / ('actual_v16_' + args.action + '_' + str(time.time_ns()) + '.json')
    create_json(path, result)
    print(json.dumps(dict(output=str(path), result=result), ensure_ascii=True))


if __name__ == '__main__':
    main()
