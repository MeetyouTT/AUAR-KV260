"""Strict metadata-only projection and SAME-board-clock timing arithmetic.

Call with an explicitly selected dictionary, never a raw runtime snapshot.
No filesystem, process, network, model, identity or database access.
"""
import math
import statistics


TIME_FIELDS = frozenset({
    'vad_last_speech_ms', 'endpoint_commit_ms', 'asr_started_ms', 'asr_finished_ms',
    'context_ms', 'llm_rpc_ms', 'tts_rpc_ms', 'first_tts_ready_ms', 'first_audio_queued_ms',
    'first_answer_sink_ms', 'playback_done_ms', 'ack_committed_ms', 'listening_rearmed_ms',
    'max_poll_gap_ms', 'guard_total_ms', 'guard_max_ms', 'progress_wait_ms',
})
COUNT_FIELDS = frozenset({'llm_calls', 'tts_calls', 'capture_overflows', 'turn_underrun_packets',
                          'turn_late_rebases', 'guard_calls', 'progress_queue_peak'})
ERROR_CODES = frozenset({'NONE', 'CANCELLED', 'DEADLINE', 'ASR_UNAVAILABLE', 'ASR_EMPTY',
    'MODEL_FAILED', 'REPLY_REJECTED', 'PERMISSION_CHANGED', 'CAPTURE_OVERFLOW',
    'AUDIO_STARVATION', 'PLAYBACK_FAILED', 'ACK_REJECTED', 'INTERNAL'})
RESULTS = frozenset({'COMPLETE', 'CANCELLED', 'FAILED', 'INCOMPLETE'})
TEST_CONTEXTS = frozenset({'UNLABELED', 'ENVIRONMENT_ONLY', 'SCRIPTED_PUBLIC', 'DIRECTED_HUMAN_TEST'})
REQUIRED = frozenset({'round_index', 'clock_domain', 'test_context', 'result', 'error_code', 'full_ack'})


def validate_round(record):
    if (not isinstance(record, dict) or not REQUIRED <= set(record)
            or set(record) - REQUIRED - TIME_FIELDS - COUNT_FIELDS):
        raise ValueError('invalid_metadata_fields')
    if (type(record['round_index']) is not int or not 1 <= record['round_index'] <= 20
            or record['clock_domain'] != 'board_monotonic'
            or not isinstance(record['test_context'], str) or record['test_context'] not in TEST_CONTEXTS
            or not isinstance(record['result'], str) or record['result'] not in RESULTS
            or not isinstance(record['error_code'], str) or record['error_code'] not in ERROR_CODES
            or record['full_ack'] is not None and type(record['full_ack']) is not bool):
        raise ValueError('invalid_metadata_enum')
    for field in TIME_FIELDS:
        value = record.get(field)
        if value is not None and (type(value) not in (int, float)
                or not math.isfinite(value) or not 0 <= value <= 300000):
            raise ValueError('invalid_metadata_time')
    for field in COUNT_FIELDS:
        value = record.get(field)
        maximum = 128 if field == 'progress_queue_peak' else 1000000
        if value is not None and (type(value) is not int or not 0 <= value <= maximum):
            raise ValueError('invalid_metadata_count')
    if record['result'] == 'COMPLETE' and (record['full_ack'] is not True or record['error_code'] != 'NONE'):
        raise ValueError('inconsistent_completion')
    # Return newly allocated whitelisted scalar values; no nested payloads.
    return {field: record.get(field) for field in sorted(REQUIRED | TIME_FIELDS | COUNT_FIELDS)}


def summarize_round(record):
    checked = validate_round(record)
    def delta(end, start):
        left, right = checked[end], checked[start]
        if left is None or right is None:
            return None
        if left < right:
            raise ValueError('inconsistent_time_order')
        return left - right
    return dict(round_index=checked['round_index'], test_context=checked['test_context'], result=checked['result'],
        error_code=checked['error_code'], full_ack=checked['full_ack'],
        endpoint_silence_ms=delta('endpoint_commit_ms', 'vad_last_speech_ms'),
        asr_ms=delta('asr_finished_ms', 'asr_started_ms'),
        vad_stop_to_first_queue_ms=delta('first_audio_queued_ms', 'vad_last_speech_ms'),
        vad_stop_to_sink_software_ms=delta('first_answer_sink_ms', 'vad_last_speech_ms'),
        queue_to_sink_software_ms=delta('first_answer_sink_ms', 'first_audio_queued_ms'),
        ack_to_rearm_ms=delta('listening_rearmed_ms', 'ack_committed_ms'),
        acoustic_first_sound_measured=False)


def summarize_group(records, *, test_context):
    if not isinstance(records, (list, tuple)) or not 1 <= len(records) <= 20:
        raise ValueError('invalid_round_count')
    if not isinstance(test_context, str) or test_context not in TEST_CONTEXTS:
        raise ValueError('invalid_test_context')
    rows = [summarize_round(record) for record in records]
    if len({row['round_index'] for row in rows}) != len(rows):
        raise ValueError('duplicate_round_index')
    complete = [row for row in rows if row['result'] == 'COMPLETE' and row['test_context'] == test_context]
    result = {'round_count': len(rows), 'complete_round_count': len(complete),
              'counts_by_result': {kind: sum(row['result'] == kind for row in rows) for kind in sorted(RESULTS)},
              'counts_by_test_context': {kind: sum(row['test_context'] == kind for row in rows) for kind in sorted(TEST_CONTEXTS)},
              'statistics_test_context': test_context, 'statistics_population': 'COMPLETE_ROUNDS_IN_EXPLICIT_CONTEXT_ONLY',
              'human_acceptance_established': False, 'acoustic_first_sound_measured': False}
    for field in ('endpoint_silence_ms', 'asr_ms', 'vad_stop_to_first_queue_ms',
                  'vad_stop_to_sink_software_ms', 'queue_to_sink_software_ms', 'ack_to_rearm_ms'):
        values = sorted(row[field] for row in complete if row[field] is not None)
        result[field] = {'n': len(values), 'p50': statistics.median(values) if values else None,
                         'p95_nearest_rank': values[math.ceil(.95 * len(values)) - 1] if values else None}
    return result
