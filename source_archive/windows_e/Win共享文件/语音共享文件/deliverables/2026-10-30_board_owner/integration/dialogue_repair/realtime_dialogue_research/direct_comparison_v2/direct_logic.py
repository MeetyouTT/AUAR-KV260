"""Pure four-call comparison logic; no services or model calls on import."""
import copy
import math
import time

from name_semantics import assess_name

QUESTION = '你叫什么名字？'
METRICS = frozenset({'prompt_eval_count','prompt_eval_cached_count','eval_count','load_duration_ms',
    'prompt_eval_duration_ms','eval_duration_ms','total_duration_ms','first_packet_ms','first_content_ms',
    'first_json_closed_ms','backend_done_ms','json_closed_to_done_ms','thinking_characters',
    'content_characters','trailing_whitespace_characters'})


def model_messages(mode, selected, canonical_prompt, compact_prompt):
    if (not isinstance(selected,list) or not selected
            or selected[0] != {'role':'system','content':canonical_prompt}):
        raise ValueError('static_prompt_mismatch')
    result=copy.deepcopy(selected)
    if mode=='dialogue_abc_v1':
        result[0]['content']=compact_prompt
    elif mode!='json':
        raise ValueError('invalid_direct_arm')
    if result[1:]!=selected[1:]:
        raise ValueError('non_system_messages_changed')
    return result


def abba(infer, guard, *, messages, candidate, validate_reply, decode_reply, cycles=1):
    if cycles != 1 or type(cycles) is not int:
        raise ValueError('direct_pilot_is_exactly_four_calls')
    immutable = copy.deepcopy(messages)
    rows, transient_speech = [], []
    for label in ('A','B','B','A'):
        guard()
        started = time.monotonic()
        row = {'trial_index':len(rows)+1,'arm':label,'complete_json':False,
               'semantic_check':'NOT_RUN','semantic_reason':'NOT_RUN','error_code':'NONE'}
        speech = None
        try:
            result = infer('json' if label == 'A' else candidate, copy.deepcopy(immutable))
            canonical = decode_reply(result['text'], label)
            reply = validate_reply(canonical, QUESTION)
            speech = reply.text
            row.update(complete_json=True, reply_characters=len(speech), **assess_name(speech),
                metrics={key:value for key,value in result.get('metrics',{}).items()
                    if key in METRICS and type(value) in (int,float) and math.isfinite(value) and 0 <= value < 1e15})
        except TimeoutError:
            row['error_code'] = 'DEADLINE'
        except InterruptedError:
            row['error_code'] = 'CANCELLED'
        except Exception as exc:
            row['error_code'] = ('OUTPUT_TRUNCATED' if type(exc).__name__ == 'OutputTruncated'
                                 else 'INVALID_OR_FAILED_REPLY')
        row['llm_wall_ms'] = (time.monotonic()-started)*1000
        if messages != immutable:
            raise ValueError('prompt_mutated')
        guard()
        transient_speech.append(speech)
        rows.append(row)
    comparisons = []
    for i in (0,3):
        for j in (1,2):
            valid = transient_speech[i] is not None and transient_speech[j] is not None
            comparisons.append({'A_trial':i+1,'B_trial':j+1,
                'exact_speech_equal':transient_speech[i] == transient_speech[j] if valid else None,
                'same_speech_length':len(transient_speech[i]) == len(transient_speech[j]) if valid else None,
                'both_name_checks_pass':rows[i]['semantic_check'] == rows[j]['semantic_check'] == 'PASS'})
    # Only booleans/counts leave the function. No reply hashes or raw strings.
    return {'trials':rows,'speech_comparisons':comparisons,
            'all_cross_arm_speech_identical':all(item['exact_speech_equal'] is True for item in comparisons)}
