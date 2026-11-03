"""Synthetic only: no devices, model requests, databases, services or wall waits."""
import ast
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import random
import sys
import threading
import types
import unittest

ROOT = Path(__file__).resolve().parents[1]
AURA = ROOT.parents[4] / 'aura'
sys.path[:0] = [str(ROOT / 'candidate'), str(ROOT), str(AURA)]
from dialogue_chunk_policy import ChunkPolicyError, segment_reply
from supply_budget import estimate_supply, validate_packets
from metadata_contract import validate_round, summarize_round, summarize_group
from build_review_patch import patched_source, REFERENCE


class ChunkTests(unittest.TestCase):
    def test_complete_meaningful_first_sentence_can_be_delivered_separately(self):
        text = '我建议今天先休息一下。第二句。第三句。第四句。'
        self.assertEqual(segment_reply(text), ('我建议今天先休息一下。', '第二句。第三句。第四句。'))

    def test_short_acknowledgement_is_not_its_own_tts_request(self):
        text = '好的！我会先核对版本，再继续处理。最后把结果告诉你。'
        chunks = segment_reply(text)
        self.assertTrue(chunks[0].startswith('好的！我会先核对版本'))
        self.assertEqual(''.join(chunks), text)

    def test_single_short_reply_remains_complete(self):
        self.assertEqual(segment_reply('你好！'), ('你好！',))

    def test_substantive_terse_answer_is_not_merged_like_filler(self):
        for text in ('先别删除！请先核对备份。', '我是雪妃。很高兴见到你。'):
            chunks = segment_reply(text)
            self.assertTrue(text.startswith(chunks[0]))
            self.assertLess(len(chunks[0]), len(text))

    def test_nested_quotes_and_closing_marks_stay_with_sentence(self):
        text = '她说：“先停一下！再核对版本。”确认后才继续。最后说明结果。'
        chunks = segment_reply(text, first_min_content=1, tail_target_content=1)
        self.assertEqual(chunks[0], '她说：“先停一下！再核对版本。”')
        self.assertEqual(''.join(chunks), text)

    def test_bracketed_punctuation_does_not_make_fragments(self):
        text = '说明（先检查！再确认。）已经写好。随后继续工作。'
        chunks = segment_reply(text, first_min_content=1, tail_target_content=1)
        self.assertEqual(chunks[0], '说明（先检查！再确认。）已经写好。')

    def test_decimal_and_url_query_are_preserved(self):
        text = '温度是3.14度。请看https://example.org/path?a=1&b=2，之后再确认。'
        chunks = segment_reply(text, first_min_content=1, tail_target_content=1)
        self.assertIn('https://example.org/path?a=1&b=2', ''.join(chunks))
        self.assertTrue(any('3.14' in chunk for chunk in chunks))
        self.assertFalse(any(chunk.endswith('?') for chunk in chunks))

    def test_large_sentence_uses_external_comma_only_when_required(self):
        text = '首先' + '甲' * 18 + '，' + '其次' + '乙' * 18 + '，' + '最后' + '丙' * 18 + '。'
        chunks = segment_reply(text, max_chars=30)
        self.assertEqual(''.join(chunks), text)
        self.assertTrue(all(len(chunk) <= 30 for chunk in chunks))

    def test_unbroken_long_identifier_fails_closed(self):
        with self.assertRaisesRegex(ChunkPolicyError, '^no_safe_boundary$'):
            segment_reply('标识' + 'a' * 240)

    def test_numeric_separators_are_not_safe_chunk_boundaries(self):
        with self.assertRaises(ChunkPolicyError):
            segment_reply('1,234,567,890', max_chars=5)

    def test_long_quote_without_external_boundary_fails_closed(self):
        with self.assertRaises(ChunkPolicyError):
            segment_reply('“' + ('内容，' * 80) + '”')

    def test_punctuation_only_does_not_reach_tts(self):
        with self.assertRaisesRegex(ChunkPolicyError, '^invalid_text$'):
            segment_reply('！？……')

    def test_invalid_inputs_never_appear_in_exception_messages(self):
        for text in (None, 1, '', 'SECRET\x00TEXT', 'x' * 501):
            with self.subTest(kind=type(text).__name__):
                with self.assertRaises(ChunkPolicyError) as context:
                    segment_reply(text)
                self.assertIn(str(context.exception), {'invalid_text'})

    def test_invalid_limits_and_bool_are_rejected(self):
        for limit in (0, 241, True, 4., '220'):
            with self.subTest(limit=limit):
                with self.assertRaisesRegex(ChunkPolicyError, '^invalid_limit$'):
                    segment_reply('有效回答。', max_chars=limit)

    def test_all_valid_wire_limits_keep_exact_text(self):
        for limit in (1, 8, 48, 220, 240):
            text = 'a' if limit == 1 else '公开文本。'
            self.assertEqual(''.join(segment_reply(text, max_chars=limit)), text)

    def test_seeded_1000_conversations_preserve_content_order_and_bound(self):
        rng = random.Random(8701)
        for _ in range(1000):
            units = []
            for _ in range(rng.randint(1, 10)):
                word = ''.join(rng.choice('春天阳光清风慢慢说话123ABC') for _ in range(rng.randint(1, 22)))
                units.append(('“' + word + '！”' if rng.random() < .2 else word + rng.choice('。！？；')))
            text = ''.join(units)
            chunks = segment_reply(text, max_chars=48)
            self.assertEqual(''.join(chunks), text)
            self.assertTrue(all(chunk and len(chunk) <= 48 for chunk in chunks))
            self.assertTrue(all(any(char.isalnum() for char in chunk) for chunk in chunks))


class SupplyTests(unittest.TestCase):
    def test_regular_delivery_needs_no_extra_start_delay(self):
        records = [dict(arrival_ms=index * 20, samples=480) for index in range(20)]
        result = estimate_supply(records)
        self.assertEqual(result.total_supply_gap_ms, 0)
        self.assertEqual(result.required_extra_start_ms, 0)
        self.assertEqual(result.last_play_end_ms, 400)

    def test_short_jitter_can_be_absorbed_at_explicit_latency_cost(self):
        records = [dict(arrival_ms=at, samples=480) for at in [0, 20, 40, 180, 180, 180, 180]]
        unbuffered = estimate_supply(records)
        buffered = estimate_supply(records, start_reserve_ms=120)
        self.assertEqual(unbuffered.total_supply_gap_ms, 120)
        self.assertEqual(buffered.total_supply_gap_ms, 0)
        self.assertEqual(buffered.first_play_ms - unbuffered.first_play_ms, 120)
        self.assertEqual(unbuffered.samples, buffered.samples)

    def test_seconds_of_supply_deficit_are_not_fixed_by_small_buffer(self):
        records = [dict(arrival_ms=at, samples=480) for at in (0, 2000)]
        result = estimate_supply(records, start_reserve_ms=240)
        self.assertEqual(result.required_extra_start_ms, 1980)
        self.assertEqual(result.total_supply_gap_ms, 1740)

    def test_burst_reports_excess_backlog_without_dropping_samples(self):
        result = estimate_supply([dict(arrival_ms=0, samples=480) for _ in range(20)])
        self.assertFalse(result.pending_within_limit)
        self.assertEqual(result.peak_pending_audio_ms, 400)
        self.assertEqual(result.samples, 9600)

    def test_partial_last_packet_has_exact_duration(self):
        result = estimate_supply([dict(arrival_ms=0, samples=480), dict(arrival_ms=20, samples=240)])
        self.assertEqual(result.last_play_end_ms, 30)

    def test_missing_fields_and_raw_payload_are_rejected(self):
        for record in ({'arrival_ms': 0}, {'arrival_ms': 0, 'samples': 480, 'pcm': 'PRIVATE'},
                       {'arrival_ms': 0, 'samples': 480, 'request_id': 'PRIVATE'}):
            with self.subTest(keys=list(record)):
                with self.assertRaisesRegex(ValueError, '^invalid_packet_fields$'):
                    validate_packets([record])

    def test_nonfinite_backwards_or_wrong_type_values_are_rejected(self):
        for at in (float('nan'), float('inf'), -1, True, '10'):
            with self.subTest(at=at):
                with self.assertRaises(ValueError):
                    validate_packets([dict(arrival_ms=at, samples=480)])
        with self.assertRaises(ValueError):
            validate_packets([dict(arrival_ms=20, samples=480), dict(arrival_ms=10, samples=480)])
        for samples in (0, 481, True, 480.):
            with self.subTest(samples=samples):
                with self.assertRaises(ValueError):
                    validate_packets([dict(arrival_ms=0, samples=samples)])

    def test_record_count_and_reserve_are_bounded(self):
        with self.assertRaises(ValueError):
            validate_packets([dict(arrival_ms=0, samples=480)] * 1501)
        for reserve in (241, -1, float('nan'), True):
            with self.subTest(reserve=reserve):
                with self.assertRaises(ValueError):
                    estimate_supply([dict(arrival_ms=0, samples=480)], start_reserve_ms=reserve)

    def test_seeded_200_arrival_traces_respect_causal_lower_bound(self):
        rng = random.Random(16)
        for _ in range(200):
            at = 0.
            records = []
            for _ in range(20):
                at += rng.choice((0, 10, 20, 30))
                records.append(dict(arrival_ms=at, samples=480))
            initial = estimate_supply(records)
            if initial.required_extra_start_ms <= 240:
                covered = estimate_supply(records, start_reserve_ms=initial.required_extra_start_ms)
                self.assertAlmostEqual(covered.total_supply_gap_ms, 0)
            self.assertGreaterEqual(initial.peak_pending_audio_ms, 0)


class MetadataTests(unittest.TestCase):
    def record(self, **kwargs):
        return dict(round_index=1, clock_domain='board_monotonic', test_context='SCRIPTED_PUBLIC', result='COMPLETE',
                    error_code='NONE', full_ack=True, **kwargs)

    def test_missing_measurements_remain_null(self):
        result = summarize_round(self.record(first_audio_queued_ms=10000))
        self.assertIsNone(result['queue_to_sink_software_ms'])
        self.assertIsNone(result['vad_stop_to_sink_software_ms'])
        self.assertFalse(result['acoustic_first_sound_measured'])

    def test_actual_same_clock_stages_are_separate(self):
        result = summarize_round(self.record(vad_last_speech_ms=100, endpoint_commit_ms=800,
            asr_started_ms=820, asr_finished_ms=3820, first_audio_queued_ms=10000,
            first_answer_sink_ms=10080, ack_committed_ms=12000, listening_rearmed_ms=12500))
        self.assertEqual(result['endpoint_silence_ms'], 700)
        self.assertEqual(result['asr_ms'], 3000)
        self.assertEqual(result['queue_to_sink_software_ms'], 80)
        self.assertEqual(result['ack_to_rearm_ms'], 500)

    def test_raw_text_pcm_ids_and_exception_details_are_rejected(self):
        for field in ('text', 'pcm', 'profile_id', 'request_id', 'exception'):
            record = self.record()
            record[field] = 'PRIVATE'
            with self.subTest(field=field):
                with self.assertRaisesRegex(ValueError, '^invalid_metadata_fields$'):
                    validate_round(record)

    def test_error_values_are_fixed_enum(self):
        record = self.record()
        record['error_code'] = 'SECRET exception text'
        with self.assertRaisesRegex(ValueError, '^invalid_metadata_enum$'):
            validate_round(record)

    def test_other_clock_domain_cannot_be_subtracted(self):
        record = self.record()
        record['clock_domain'] = 'windows_monotonic'
        with self.assertRaises(ValueError): validate_round(record)

    def test_nonfinite_negative_bool_and_nested_time_are_rejected(self):
        for value in (float('nan'), float('inf'), -1, True, {'text': 'PRIVATE'}):
            with self.subTest(value=value):
                with self.assertRaises(ValueError): validate_round(self.record(context_ms=value))

    def test_backwards_time_and_false_complete_ack_are_rejected(self):
        with self.assertRaisesRegex(ValueError, '^inconsistent_time_order$'):
            summarize_round(self.record(first_audio_queued_ms=100, first_answer_sink_ms=80))
        record = self.record()
        record['full_ack'] = False
        with self.assertRaisesRegex(ValueError, '^inconsistent_completion$'): validate_round(record)

    def test_group_reports_n_for_missing_and_measured_fields(self):
        records = [self.record(vad_last_speech_ms=0, first_answer_sink_ms=100)]
        record = self.record(vad_last_speech_ms=0, first_audio_queued_ms=90)
        record['round_index'] = 2
        records.append(record)
        result = summarize_group(records, test_context='SCRIPTED_PUBLIC')
        self.assertEqual(result['vad_stop_to_sink_software_ms']['n'], 1)
        self.assertEqual(result['vad_stop_to_sink_software_ms']['p50'], 100)
        self.assertEqual(result['ack_to_rearm_ms']['n'], 0)
        self.assertIsNone(result['ack_to_rearm_ms']['p50'])

    def test_cancelled_rounds_are_counted_but_not_mixed_into_completed_latency(self):
        complete = self.record(vad_last_speech_ms=0, first_answer_sink_ms=100)
        cancelled = dict(complete, round_index=2, result='CANCELLED', error_code='CANCELLED',
                         full_ack=False, first_answer_sink_ms=20)
        result = summarize_group([complete, cancelled], test_context='SCRIPTED_PUBLIC')
        self.assertEqual(result['complete_round_count'], 1)
        self.assertEqual(result['counts_by_result']['CANCELLED'], 1)
        self.assertEqual(result['vad_stop_to_sink_software_ms']['p50'], 100)

    def test_environment_triggered_round_is_not_user_acceptance_or_mixed_latency(self):
        scripted = self.record(vad_last_speech_ms=0, first_answer_sink_ms=100)
        environment = dict(scripted, round_index=2, test_context='ENVIRONMENT_ONLY', first_answer_sink_ms=20)
        result = summarize_group([scripted, environment], test_context='SCRIPTED_PUBLIC')
        self.assertEqual(result['counts_by_test_context']['ENVIRONMENT_ONLY'], 1)
        self.assertEqual(result['vad_stop_to_sink_software_ms']['n'], 1)
        self.assertEqual(result['vad_stop_to_sink_software_ms']['p50'], 100)
        self.assertFalse(result['human_acceptance_established'])


def _module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


policy = _module('board.runtime.dialogue_chunk_policy', ROOT / 'candidate/dialogue_chunk_policy.py')
original_source, changed_source = patched_source()
dialogue = types.ModuleType('research_pinned_board_dialogue')
dialogue.__file__ = str(REFERENCE)
sys.modules[dialogue.__name__] = dialogue
exec(compile(changed_source, str(REFERENCE), 'exec'), dialogue.__dict__)
from common.model_inference_wire import Owner, audio_payload, make_response


class FakeStore:
    def __init__(self):
        self.events, self.valid = [], True
    def preempt_compaction(self): self.events.append('preempt')
    def begin_turn(self, *args, **kwargs):
        self.events.append('begin')
        return {'user_event_id': 'synthetic-event'}
    def context(self, *args, **kwargs): return {'messages': [], 'facts': []}
    def generated(self, *args, **kwargs): self.events.append('generated')
    def check_prepared_turn_current(self, *args, **kwargs):
        self.events.append('check')
        if not self.valid: raise PermissionError('synthetic_revoked')
    def bind_audio_receipt(self, *args, **kwargs): self.events.append('bound')
    def ack_played(self, *args, **kwargs):
        self.events.append('acked')
        return {'complete': kwargs['complete']}
    def interrupt(self, *args, **kwargs): self.events.append('interrupted')


class FakeModels:
    def __init__(self, raw): self.raw, self.calls = raw, []
    def request(self, kind, payload, **kwargs):
        self.calls.append((kind, payload))
        result = ({'text': self.raw} if kind == 'llm'
                  else {'audio': audio_payload(b'\x01\x00' * 480, 24000)})
        return make_response(Owner.from_dict(payload), result=result)
    def cancel(self, owner): pass


class IntegrationTests(unittest.TestCase):
    def make(self, text='我建议今天先休息一下。第二句。第三句。第四句。', raw=None):
        store = FakeStore()
        models = FakeModels(raw if raw is not None else json.dumps(
            {'reply_text': text, 'emotion': 'friendly', 'avatar_action': ''}, ensure_ascii=False))
        controller = dialogue.BoardDialogueController(store, models, board_boot_id='synthetic-boot',
            system_prompt='合成测试人格', clock=lambda: 10.)
        return controller, store, models

    def prepare(self, controller, **kwargs):
        return controller.prepare_text('公开合成测试输入', scope={'kind': 'conversation', 'id': 'synthetic'},
            session_id='synthetic-session', generation=1, budget_ms=10000, **kwargs)

    def test_existing_splitter_local_sequences_and_other_methods_stay_unchanged(self):
        def remaining(source):
            tree = ast.parse(source)
            kept = []
            for node in tree.body:
                if isinstance(node, ast.FunctionDef) and node.name == 'split_dialogue_sentences':
                    continue
                if isinstance(node, ast.ClassDef) and node.name == 'BoardDialogueController':
                    node.body = [child for child in node.body
                                 if not isinstance(child, ast.FunctionDef) or child.name != '_prepare']
                kept.append(ast.dump(node))
            return kept
        self.assertEqual(remaining(original_source), remaining(changed_source))

    def test_local_command_reply_keeps_original_sentence_policy(self):
        controller, _, models = self.make()
        text = '我建议今天先休息一下。第二句。第三句。第四句。'
        controller.command_handler = lambda *args, **kwargs: dialogue.BoardReply(text)
        plan = self.prepare(controller, chunk_sink=lambda *args: None)
        self.assertEqual(len(plan.chunks), 4)
        self.assertTrue(all(kind == 'tts' for kind, _ in models.calls))

    def test_first_chunk_precedes_later_tts_and_full_receipt_is_preserved(self):
        controller, store, models = self.make()
        observed = []
        def sink(chunk, reply, start, token):
            observed.append((chunk, start, token, len(models.calls)))
            self.assertIn('generated', store.events)
            self.assertNotIn('bound', store.events)
        plan = self.prepare(controller, chunk_sink=sink)
        self.assertEqual([item[3] for item in observed], [2, 3])
        self.assertEqual([item[1] for item in observed], [0, 480])
        self.assertTrue(all(item[2] == plan.playback_token for item in observed))
        self.assertEqual(plan.sha256, hashlib.sha256(plan.pcm).hexdigest())
        self.assertEqual(''.join(chunk.text for chunk in plan.chunks), plan.reply.text)
        self.assertNotIn('acked', store.events)
        controller.acknowledge(plan, playback_token=plan.playback_token, sha256=plan.sha256,
                               samples=plan.samples, complete=True)
        self.assertIn('acked', store.events)

    def test_incomplete_json_never_reaches_tts(self):
        controller, store, models = self.make(raw='{"reply_text":"合成测试')
        with self.assertRaises(dialogue.ReplyRejected): self.prepare(controller)
        self.assertEqual([kind for kind, _ in models.calls], ['llm'])
        self.assertNotIn('generated', store.events)

    def test_thinking_text_never_reaches_tts(self):
        controller, _, models = self.make(text='<think>合成内容</think>')
        with self.assertRaises(dialogue.ReplyRejected): self.prepare(controller)
        self.assertEqual([kind for kind, _ in models.calls], ['llm'])

    def test_unsafe_long_reply_is_rejected_before_any_tts(self):
        controller, store, models = self.make(text='甲' * 241)
        with self.assertRaises(dialogue.ReplyRejected): self.prepare(controller)
        self.assertEqual([kind for kind, _ in models.calls], ['llm'])
        self.assertNotIn('generated', store.events)

    def test_wrong_full_ack_samples_do_not_commit(self):
        controller, store, _ = self.make()
        plan = self.prepare(controller)
        with self.assertRaises(ValueError):
            controller.acknowledge(plan, playback_token=plan.playback_token, sha256=plan.sha256,
                                   samples=plan.samples - 1, complete=True)
        self.assertNotIn('acked', store.events)

    def test_cancellation_after_first_chunk_stops_remaining_tts(self):
        controller, store, models = self.make()
        def sink(*args): controller.cancel('synthetic-session', generation=1)
        with self.assertRaises(dialogue.StaleGeneration): self.prepare(controller, chunk_sink=sink)
        self.assertEqual([kind for kind, _ in models.calls], ['llm', 'tts'])
        self.assertNotIn('bound', store.events)
        self.assertNotIn('acked', store.events)

    def test_revocation_after_first_chunk_is_checked_before_next_tts(self):
        controller, store, models = self.make()
        def sink(*args): store.valid = False
        with self.assertRaises(PermissionError): self.prepare(controller, chunk_sink=sink)
        self.assertEqual([kind for kind, _ in models.calls], ['llm', 'tts'])
        self.assertNotIn('acked', store.events)


if __name__ == '__main__':
    unittest.main()
