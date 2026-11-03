"""Root serial public model comparison, always restoring listening after owned pause."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time

HERE = Path(__file__).resolve().parent
REPAIR = HERE.parent
VALID = REPAIR / 'first_wait_streaming_validation'
sys.path.insert(0, str(VALID))
from root_generate_fixtures import ssh

WAIT_IDLE = r'''
import http.client,json,time
end=time.monotonic()+60
while True:
 c=http.client.HTTPConnection('127.0.0.1',8783,timeout=4)
 try:
  c.request('GET','/api/state');r=c.getresponse();raw=r.read(1048577)
  assert r.status==200 and len(raw)<=1048576
  state=json.loads(raw)
 finally:c.close()
 enabled=state.get('handsfree_dialogue',{}).get('enabled')
 assert type(enabled) is bool,'listening_preference_unavailable'
 idle=state.get('phase')=='IDLE' and state.get('playing') is False and state.get('local_transcription',{}).get('state') not in ('TRANSCRIBING','GENERATING','PLAYING')
 if idle:break
 if time.monotonic()>=end:raise RuntimeError('idle_window_unavailable')
 time.sleep(.5)
print(json.dumps(dict(idle=True,enabled=enabled,observed_mono=time.monotonic())))
'''


def run(script, *arguments, timeout):
    completed = subprocess.run([sys.executable, '-B', str(script), *arguments],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding='utf-8', timeout=timeout)
    if completed.returncode:
        raise RuntimeError(script.stem + '_failed')
    return json.loads(completed.stdout)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    args = parser.parse_args()
    run_id = str(time.time_ns())
    path = HERE / ('PAIR_' + run_id + '.json')
    value = dict(status='STARTING', order=['paraformer','paraformer_small'],
        slots=[], production_changed=False, original_listening_restored=False)
    paused = False
    try:
        value['pre_pause'] = json.loads(ssh('python3 -B -', WAIT_IDLE, timeout=70))
        if value['pre_pause']['enabled']:
            paused = True  # Restore even if the pause helper fails after submitting its command.
            value['pause'] = run(REPAIR / 'frontend_balance_candidate/maintenance_listening.py', 'pause', timeout=80)
        else:
            value['pause'] = dict(prior_enabled=False, enabled=False, pause_command_sent=False,
                note='Existing paused preference preserved; no automatic resume without clarification.')
        began = time.monotonic()
        for engine in value['order']:
            assert time.monotonic() - began < 260, 'insufficient_remaining_pause_budget'
            result = run(HERE / 'root_run_public.py', '--engine', engine,
                '--source-sha256', '94f7ac8598628f6137ca3e3d122904d9eb4bd8627df8077de80bea423177536e', timeout=240)
            latest = max(HERE.glob('actual_public_' + engine + '_*.json'), key=lambda p: p.stat().st_mtime_ns)
            row = dict(engine=engine, status=result.get('status'), result_file=latest.name,
                result_sha256=hashlib.sha256(latest.read_bytes()).hexdigest(),
                worker_exit_code=result.get('worker_exit_code'), background_activity_changed=result.get('background_activity_changed'),
                owners_unchanged=result.get('owners_unchanged'), decode_wall_sum_ms=result.get('decode_wall_sum_ms'),
                decode_cpu_sum_ms=result.get('decode_cpu_sum_ms'), aggregate_edit_distance=result.get('aggregate_edit_distance'),
                process_peak_rss_kib=result.get('process_peak_rss_kib'))
            value['slots'].append(row)
            path.write_text(json.dumps(value, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
            print(json.dumps(dict(slot_finished=row)), flush=True)
            assert result.get('status') == 'PUBLIC_ASR_MEASURED_NOT_ACCEPTED' and result.get('worker_exit_code') == 0 and result.get('owners_unchanged') is True, 'public_slot_failed'
        value['status'] = 'PUBLIC_PAIR_FINISHED_NOT_PRODUCTION_ACCEPTANCE'
    except Exception as error:
        value['status'] = 'PAIR_STOPPED'
        value['error_type'] = type(error).__name__
    finally:
        if paused:
            try:
                value['restore'] = run(REPAIR / 'frontend_balance_candidate/maintenance_listening.py', 'resume', timeout=80)
                value['original_listening_restored'] = value['restore'].get('enabled') is True and value['restore'].get('microphone_open') is True
                observation = run(REPAIR / 'probe.py', 'paraformer_small_restore_' + run_id, timeout=30)
                value['restore_observation_file'] = '../paraformer_small_restore_' + run_id + '.json'
                value['restore_observation_sha256'] = hashlib.sha256((REPAIR / ('paraformer_small_restore_' + run_id + '.json')).read_bytes()).hexdigest()
                value['restore_state'] = dict(observed_mono=observation.get('observed_mono'),phase=observation.get('phase'),listening=observation.get('listening'),capture_performance=observation.get('capture_performance'),runtime_faults=observation.get('runtime_faults'))
            except Exception as error:
                value['restore_error_type'] = type(error).__name__
        elif value.get('pre_pause',{}).get('enabled') is False:
            try:
                observation = run(REPAIR / 'probe.py', 'paraformer_small_paused_final_' + run_id, timeout=30)
                value['restore_observation_file'] = '../paraformer_small_paused_final_' + run_id + '.json'
                value['restore_observation_sha256'] = hashlib.sha256((REPAIR / ('paraformer_small_paused_final_' + run_id + '.json')).read_bytes()).hexdigest()
                value['original_listening_preference_preserved'] = observation.get('listening',{}).get('enabled') is False
                value['restore_state'] = dict(observed_mono=observation.get('observed_mono'),phase=observation.get('phase'),listening=observation.get('listening'),capture_performance=observation.get('capture_performance'),runtime_faults=observation.get('runtime_faults'))
            except Exception as error:
                value['restore_error_type'] = type(error).__name__
        path.write_text(json.dumps(value, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
        print(json.dumps(dict(pair_finished=value)), flush=True)
