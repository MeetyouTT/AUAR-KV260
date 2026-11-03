"""Read existing receipts and emit selected numeric metadata only.

No inference, devices, sockets, imports from runtime, database access, or logs.
The explicitly selected short-round indices are not a human acceptance label.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path


HERE = Path(__file__).resolve().parent
RESEARCH = HERE.parent
REPAIR = RESEARCH.parent


def read(path):
    raw = path.read_bytes()
    return json.loads(raw.decode('utf-8-sig')), {
        'path': str(path), 'sha256': hashlib.sha256(raw).hexdigest(), 'bytes': len(raw)}


def number(mapping, key):
    value = mapping[key]
    if type(value) not in (int, float) or not 0 <= value < 1e12:
        raise ValueError('invalid_numeric_metadata')
    return float(value)


def main():
    sources = []
    data, pin = read(REPAIR / 'compact_human_round.json')
    sources.append(pin)
    # Root's three reported short rounds, plus the distinct long/outlier round.
    # No polling repetitions become additional observations.
    indices = (0, 36, 50, 22)
    rows = []
    for index in indices:
        sample = data['samples'][index]
        phase, prepare = sample['latency'], sample['prepare_latency']
        if phase.get('complete') is not True or prepare.get('complete') is not True:
            raise ValueError('selected_receipt_not_complete')
        row = {'source_sample_index': index,
               'reported_short_round': index != 22,
               'test_context': 'UNLABELED',
               'speaker_first_audio_measured': False}
        for key in ('asr_ms', 'first_audio_queued_ms', 'worker_total_ms'):
            row[key] = round(number(phase, key), 3)
        for key in ('llm_rpc_ms', 'tts_rpc_ms', 'context_ms', 'first_tts_ready_ms',
                    'first_chunk_emitted_ms', 'prepare_total_ms'):
            row[key] = round(number(prepare, key), 3)
        if number(prepare, 'llm_calls') != 1 or number(prepare, 'tts_calls') != 1:
            raise ValueError('selected_receipt_has_multiple_model_calls')
        row['unallocated_to_asr_llm_tts_context_ms'] = round(
            row['first_audio_queued_ms'] - row['asr_ms'] - row['llm_rpc_ms']
            - row['tts_rpc_ms'] - row['context_ms'], 3)
        row['arithmetic_if_asr_removed_ms'] = round(
            row['first_audio_queued_ms'] - row['asr_ms'], 3)
        row['arithmetic_if_final_asr_500ms_ms'] = round(
            row['arithmetic_if_asr_removed_ms'] + 500., 3)
        # This estimates a serial stage substitution; it is not a measured gain.
        row['arithmetic_if_final_asr_500ms_and_llm_twice_as_fast_ms'] = round(
            row['arithmetic_if_final_asr_500ms_ms'] - row['llm_rpc_ms'] / 2., 3)
        row['asr_fraction_of_queue_wait'] = round(
            row['asr_ms'] / row['first_audio_queued_ms'], 4)
        rows.append(row)

    direct, pin = read(RESEARCH / 'direct_comparison_v2' / 'benchmark_runs'
                       / 'direct_name_abba_8b8643d9d18b.json')
    sources.append(pin)
    trials = []
    wanted = ('prompt_eval_count', 'prompt_eval_cached_count', 'eval_count',
              'load_duration_ms', 'prompt_eval_duration_ms', 'eval_duration_ms',
              'json_closed_to_done_ms', 'thinking_characters',
              'trailing_whitespace_characters')
    for trial in direct['trials']:
        metrics = trial['metrics']
        trial_index = int(number(trial, 'trial_index'))
        if trial_index not in (1, 2, 3, 4):
            raise ValueError('unexpected_trial_index')
        result = {'trial_index': trial_index, 'arm': 'A' if trial_index in (1, 4) else 'B',
                  'llm_wall_ms': round(number(trial, 'llm_wall_ms'), 3),
                  'reply_characters': int(number(trial, 'reply_characters'))}
        result.update({key: number(metrics, key) for key in wanted})
        result['decode_tokens_per_second'] = round(
            result['eval_count'] * 1000. / result['eval_duration_ms'], 4)
        result['decode_ms_per_token'] = round(
            result['eval_duration_ms'] / result['eval_count'], 4)
        trials.append(result)

    public, pin = read(REPAIR / 'first_wait_integration' / 'actual_public_compact_chain.json')
    sources.append(pin)
    pmetrics = public['timings']['llm_metrics']
    public_metrics = {key: number(pmetrics, key) for key in wanted}
    current, pin = read(REPAIR / 'resume_v14_runtime.json')
    sources.append(pin)
    producer = current['producer_diagnostics']
    guard = {key: number(producer, key) for key in
             ('guard_calls', 'guard_total_ms', 'guard_thread_cpu_total_ms',
              'guard_thread_cpu_max_ms', 'progress_wait_ms')}
    guard['scope'] = 'one_current_receipt_whole_producer_not_first_packet_breakdown'

    out = {
        'schema': 'architecture_latency_numeric_v3', 'sources': sources,
        'sample_selection': 'explicit_indices_not_automatic_scene_classification',
        'short_round_source_indices': [0, 36, 50], 'other_completed_round_source_indices': [22],
        'stage_rows': rows, 'direct_name_trials': trials,
        'same_speech_across_arms': direct['all_cross_arm_speech_identical'] is True,
        'public_compact_cold_prefix_metrics': public_metrics,
        'one_current_guard_receipt': guard,
        'arithmetic_scenarios_are_not_measured_speedups': True,
        'first_chunk_emitted_is_callback_completion_not_first_audio_queued': True,
        'human_acceptance_claimed': False, 'model_calls': 0,
        'device_operations': 0, 'production_database_accesses': 0,
    }
    target = HERE / 'NUMERIC_EVIDENCE.json'
    target.write_text(json.dumps(out, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'status': 'PASS', 'stage_rows': len(rows), 'trials': len(trials),
                      'source_receipts': len(sources), 'output': str(target)}))


if __name__ == '__main__':
    main()
