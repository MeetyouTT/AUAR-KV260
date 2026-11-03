"""Public ABC/AB pilot core; root supplies original guarded inference and owner checks.

Import and default CLI perform no I/O to services/models. This module cannot
create a backend, bypass GPU admission, pause listening or operate a device.
"""
import copy
import json
import math
import re
import time

QUESTION = '请只给结果：六乘九等于多少？'
ORDER = ('dialogue_abc_v1', 'dialogue_ab_v1', 'dialogue_ab_v1', 'dialogue_abc_v1')
METRICS = frozenset(('prompt_eval_count', 'prompt_eval_cached_count', 'eval_count',
    'load_duration_ms', 'prompt_eval_duration_ms', 'eval_duration_ms', 'total_duration_ms',
    'first_content_ms', 'first_json_closed_ms', 'backend_done_ms', 'json_closed_to_done_ms',
    'thinking_characters', 'content_characters', 'trailing_whitespace_characters'))


def plan():
    return dict(status='PLAN_ONLY_NO_MODELS_OR_SERVICES_CONTACTED', order=list(ORDER),
        public_question=QUESTION, num_predict=120, num_ctx=2048, think=False,
        temperature=.6, fixed_seed_by_root_infer=8701, warmups=0,
        root_fresh_exclusive_window_and_original_gpu_admission_required=True,
        no_tts_asr_store_microphone_or_playback=True, performance_gain_measured=False)


def run_public_abba(infer, guard, *, system_prompt):
    """Exactly four calls; callbacks must retain original ownership/GPU/deadline rules.

    infer(mode, messages) is root's existing backend.llm path with a 30s
    per-request deadline and fixed 8701 seed in that isolated test process.
    guard() is root's original fresh unique-owner/idle/residency check. This
    helper makes no assertion that a callback implements those external rules.
    """
    from board.runtime.compact_request_adapter import CompactRequestAdapter
    from board.runtime.board_dialogue import validate_model_reply
    from common.inference_output_contract import canonicalize_compact
    if not callable(infer) or not callable(guard):
        raise ValueError('root_callbacks_required')
    capabilities = dict(format_contract_version=1, output_formats=['json', *set(ORDER)])
    messages = {}
    for mode in set(ORDER):
        adapter = CompactRequestAdapter(None, system_prompt=system_prompt,
            capabilities=capabilities, mode=mode)
        messages[mode] = [dict(role='system', content=adapter.translated_prompt),
                          dict(role='user', content=QUESTION)]
    rows = []
    for mode in ORDER:
        guard()
        row = dict(index=len(rows)+1, mode=mode, complete_json=False,
                   semantic_check='NOT_RUN', error_code='NONE')
        started = time.monotonic()
        try:
            result = infer(mode, copy.deepcopy(messages[mode]))
            reply = validate_model_reply(canonicalize_compact(result['text'], mode=mode), QUESTION)
            value = re.sub(r'[\s。！!，,：:；;]', '', reply.text)
            semantic = bool(re.fullmatch(
                r'(?:(?:六乘九|6[乘×x*]9)(?:的)?(?:结果|答案)?)?'
                r'(?:等于|结果是|结果为|答案是|答案为|是|为|=)?(?:54|五十四)', value))
            row.update(complete_json=True, semantic_check='PASS' if semantic else 'UNKNOWN',
                reply_characters=len(reply.text), metrics={key:value for key,value in result.get('metrics', {}).items()
                    if key in METRICS and type(value) in (int, float) and math.isfinite(value) and 0 <= value < 1e15})
        except TimeoutError:
            row['error_code'] = 'DEADLINE'
        except InterruptedError:
            row['error_code'] = 'CANCELLED'
        except Exception as exc:
            row['error_code'] = ('OUTPUT_TRUNCATED' if type(exc).__name__ == 'OutputTruncated'
                                 else 'INVALID_OR_FAILED_REPLY')
        finally:
            row['llm_wall_ms'] = (time.monotonic()-started)*1000
            rows.append(row)
        guard()
        if row['error_code'] != 'NONE':
            break  # Preserve the failed/partial trial; no hidden retries.
    return dict(schema='aura.public-abc-ab-pilot.v1', order=list(ORDER), trials=rows,
        expected_trials=4, completed_trials=len(rows), warmups=0,
        all_complete=len(rows)==4 and all(r['complete_json'] for r in rows),
        all_semantic_pass=len(rows)==4 and all(r['semantic_check']=='PASS' for r in rows),
        input_difference='Only static output-contract field obligation; user text unchanged.',
        raw_reply_prompt_or_pcm_saved=False, tts_requests=0, store_accessed=False,
        scope='LLM complete-response pilot only; neither speaker onset nor full business validation')


if __name__ == '__main__':
    print(json.dumps(plan(), ensure_ascii=False))
