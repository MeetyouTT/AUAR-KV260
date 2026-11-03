"""Offline fakes only: no imports/calls to native ASR, network or devices."""
from contextlib import nullcontext
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import unittest

HERE = Path(__file__).resolve().parent
sys.dont_write_bytecode = True
sys.path.insert(0, str(HERE / 'reference'))
spec = importlib.util.spec_from_file_location('small_chain_worker', HERE / 'public_small_model_chain.py')
worker = importlib.util.module_from_spec(spec)
spec.loader.exec_module(worker)
from common import model_inference_wire as wire
from board.runtime.board_dialogue import validate_model_reply, split_sentences
from tools.production_output_format import NegotiatedDialogueClient

PROMPT = json.loads((HERE / 'reference/config/character_profile.local.json').read_bytes())['persona_full_prompt']
PUBLIC = '你好，请用两句话介绍你自己。'
REPLY = '我是雪妃，可以陪你交流，也可以介绍我擅长的事情和回答普通问题。你可以直接说出自己的想法，让我们慢慢聊一聊。'


class FakeClock:
    def __init__(self):
        self.now = 0.0
    def __call__(self):
        return self.now
    def advance(self, seconds):
        self.now += seconds


class FakeAsr:
    def __init__(self, clock, fail=False):
        self.clock, self.fail = clock, fail
        self.calls = 0
    def transcribe(self, pcm, *, sample_rate, deadline, cancelled):
        self.calls += 1
        if self.fail:
            raise TimeoutError('not exposed')
        assert pcm == b'\x01\x00' * 32 and sample_rate == 16000
        assert self.clock() < deadline and not cancelled()
        self.clock.advance(1.5)
        return PUBLIC


class FakeTransport:
    def __init__(self, clock, mode='ok'):
        self.clock, self.mode = clock, mode
        self.sent, self.cancelled = [], []
    def output_format_capabilities(self):
        return dict(format_contract_version=1, output_formats=['json', 'dialogue_abc_v1'])
    def request(self, kind, payload, *, deadline, cancelled):
        wire.validate_request(kind, payload)
        assert self.clock() < deadline and not cancelled()
        self.sent.append((kind, payload))
        owner = wire.Owner.from_dict(payload)
        if kind == 'llm':
            self.clock.advance(3)
            assert payload['options']['output_format'] == 'dialogue_abc_v1'
            assert payload['messages'][1]['content'] == PUBLIC
            assert 'reply_text' not in payload['messages'][0]['content']
            raw = json.dumps(dict(a=REPLY, b='friendly', c=''), ensure_ascii=False)
            if self.mode == 'malformed':
                raw = '{"a":"not closed'
            response = wire.make_response(owner, result=dict(text=raw, metrics=dict(eval_count=31)))
            if self.mode == 'stale_owner':
                response['generation'] += 1
            return response
        self.clock.advance(1)
        if self.mode == 'tts_timeout':
            raise TimeoutError('do not expose reply')
        data = b'\x02\x00' * 240
        audio = wire.audio_payload(data)
        if self.mode == 'invalid_audio':
            audio['sha256'] = '0' * 64
        return wire.make_response(owner, result=dict(audio=audio))
    def cancel(self, owner):
        self.cancelled.append(owner)
        self.clock.advance(.01)
        if self.mode == 'cancel_fail':
            return None
        return wire.make_response(owner, result=dict(cancelled=False, state='completed'))


class PublicChainTests(unittest.TestCase):
    def run_fixture(self, mode='ok', asr_fail=False):
        clock = FakeClock()
        transport = FakeTransport(clock, mode)
        client = NegotiatedDialogueClient(transport, system_prompt=PROMPT, mode='dialogue_abc_v1')
        asr = FakeAsr(clock, asr_fail)
        loads = []
        def load():
            loads.append(True)
            clock.advance(2)
            return asr
        result = worker.run_case(asr_factory=load, client=client, prompt=PROMPT,
            pcm=b'\x01\x00' * 32, reference=PUBLIC, boot=worker.BOOT, deadline=65,
            wire=wire, validate_reply=validate_model_reply, split_reply=split_sentences,
            quiet=nullcontext, clock=clock, cpu_clock=clock)
        self.assertEqual(len(loads), 1)
        self.assertEqual(asr.calls, 1)
        self.assertEqual(len(transport.cancelled), len(transport.sent))
        self.assertEqual([x.request_id for x in transport.cancelled],
                         [x[1]['request_id'] for x in transport.sent])
        serialized = json.dumps(result, ensure_ascii=False)
        self.assertNotIn(PUBLIC, serialized)
        self.assertNotIn(REPLY, serialized)
        self.assertNotIn('pcm_base64', serialized)
        return result, transport

    def test_exact_v16_source_refs_and_helper_pin(self):
        mapping = json.loads((HERE.parent / 'v16_evidence/source_mapping.json').read_bytes())
        self.assertEqual(mapping['startup_sha256'], worker.STARTUP_SHA)
        for relative, expected in worker.PINS.items():
            self.assertEqual(mapping['component_pins'][relative], expected)
            if relative != 'config/board_avatar_gtk.json':
                self.assertEqual(worker.sha((HERE / 'reference' / relative).read_bytes()), expected)
        helper = HERE.parents[1] / 'first_wait_streaming_validation/quality/public_quality_worker.py'
        self.assertEqual(worker.sha(helper.read_bytes()), worker.HELPER_SHA)
        self.assertEqual(worker.sha(PROMPT.encode()), worker.PROMPT_SHA)

    def test_formal_abc_complete_reply_no_old_48_limit_and_timings(self):
        result, transport = self.run_fixture()
        self.assertGreater(len(REPLY), 48)
        self.assertTrue(result['status'].startswith('PASS_'))
        self.assertEqual([x[0] for x in transport.sent], ['llm', 'tts', 'tts'])
        self.assertEqual(''.join(p['text'] for kind, p in transport.sent if kind == 'tts'), REPLY)
        timing = result['timings']
        self.assertEqual(timing['asr_model_load_and_pin_wall_ms'], 2000)
        self.assertEqual(timing['asr_decode_wall_ms'], 1500)
        self.assertEqual(timing['asr_completion_to_complete_ram_audio_ms'], 5000)
        self.assertEqual(timing['asr_decode_start_to_complete_ram_audio_ms'], 6500)
        self.assertEqual(timing['asr_completion_to_first_ram_audio_ms'], 4000)
        self.assertEqual(timing['asr_decode_start_to_first_ram_audio_ms'], 5500)
        self.assertEqual(result['audio']['samples'], 480)
        self.assertTrue(result['owned_cleanup_confirmed'])

    def test_malformed_or_stale_full_reply_blocks_all_tts(self):
        for mode in ('malformed', 'stale_owner'):
            with self.subTest(mode=mode):
                result, transport = self.run_fixture(mode)
                self.assertEqual(result['status'], 'FAIL')
                self.assertEqual(result['error_stage'], 'LLM_COMPLETE_REPLY')
                self.assertEqual([x[0] for x in transport.sent], ['llm'])

    def test_tts_failure_and_corrupt_audio_are_cleaned_and_never_pass(self):
        for mode in ('tts_timeout', 'invalid_audio'):
            with self.subTest(mode=mode):
                result, transport = self.run_fixture(mode)
                self.assertEqual(result['status'], 'FAIL')
                self.assertEqual(result['error_stage'], 'TTS_COMPLETE_RAM_AUDIO')
                self.assertNotIn('audio', result)
                self.assertEqual(len(transport.cancelled), 2)

    def test_asr_failure_never_requests_llm_or_tts(self):
        result, transport = self.run_fixture(asr_fail=True)
        self.assertEqual(result['error_stage'], 'ASR_TRANSCRIBE')
        self.assertFalse(transport.sent)

    def test_unconfirmed_cancel_cannot_report_pass(self):
        result, _ = self.run_fixture('cancel_fail')
        self.assertEqual(result['status'], 'FAIL_OWNED_CLEANUP_UNCONFIRMED')
        self.assertFalse(result['owned_cleanup_confirmed'])


if __name__ == '__main__':
    unittest.main(verbosity=2)
