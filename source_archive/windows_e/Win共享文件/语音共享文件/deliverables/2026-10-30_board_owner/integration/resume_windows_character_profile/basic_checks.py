"""Small source/prompt checks only: no model, service, device or business DB."""
import ast
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT/'aura'))
from common.character_profile import selected_profile, load_profile, CharacterProfileError
from common.device_policy import MODEL_HINT
from common.spoken_input import SPEECH_INPUT_HINT, prepare_spoken_input
from common.voice_wake import wake_request
from common.voice_enrollment import identity_query_requested
from common.binding_intent import binding_intent
from common.memory_commands import parse_command
from tools.dialogue_host_ollama import fast_system_prompt, build_system_prompt
from tools.dialogue_stream import stream_body


class ProfileChecks(unittest.TestCase):
    def test_default_selection_and_missing_or_changed_config_fail_closed(self):
        profile = selected_profile()
        self.assertIs(profile, selected_profile())
        self.assertEqual((profile.display_name, profile.asr_aliases), ('雪妃', ()))
        value = json.loads((ROOT/'aura/config/character_profile.local.json').read_text(encoding='utf-8'))
        with tempfile.TemporaryDirectory(prefix='aura-public-profile-') as temporary:
            path = Path(temporary)/'selection.json'
            with self.assertRaises(CharacterProfileError): load_profile(path)
            value['profile_version'] = 'unreviewed'
            path.write_text(json.dumps(value), encoding='utf-8')
            with self.assertRaises(CharacterProfileError): load_profile(path)

    def test_same978_byte_prompt_and_json_contract_without_device_hint_duplication(self):
        profile = selected_profile()
        body = stream_body('public-no-model-call', [], '你好。')
        self.assertEqual(body['messages'][0]['content'], profile.persona_full_prompt)
        self.assertEqual(len(profile.persona_full_prompt.encode('utf-8')), 978)
        self.assertEqual(hashlib.sha256(profile.persona_full_prompt.encode()).hexdigest(),
                         '11b1b4d04c55ac110969fd5dd7ffb37f29b29bbc26d9c7906e454d4f69af654e')
        self.assertEqual(profile.persona_full_prompt.count(MODEL_HINT), 1)
        self.assertIn(SPEECH_INPUT_HINT, profile.persona_full_prompt)
        self.assertEqual(len(fast_system_prompt().encode()), 614)
        self.assertEqual(set(body['format']['properties']), {'reply_text','emotion','avatar_action'})
        self.assertEqual(body['format']['properties']['emotion']['enum'], ['neutral','friendly','happy','sad'])
        self.assertEqual(body['format']['properties']['avatar_action']['enum'], [''])
        self.assertIn('雪妃', build_system_prompt([], []))
        self.assertNotIn('汐蓝', build_system_prompt([], []))

    def test_reasoning_keeps_existing200_character_rule(self):
        body = stream_body('public-no-model-call', [], '请核算。', think=True)
        self.assertIn('最多200个中文字', body['messages'][0]['content'])
        self.assertNotIn('最多48个中文字', body['messages'][0]['content'])
        self.assertEqual(body['options']['num_ctx'], 2048)

    def test_new_addresses_without_rewriting_literal_user_names(self):
        self.assertEqual(wake_request('雪妃，今天聊什么'), '今天聊什么')
        self.assertEqual(wake_request('御笠雪妃，在吗'), '在吗')
        self.assertEqual(wake_request('欸'), '')
        self.assertEqual(wake_request('哎'), '')
        self.assertIsNone(wake_request('哎呀'))
        self.assertIsNone(wake_request('汐蓝'))
        text = '我叫西兰，不是雪妃。'
        self.assertEqual(prepare_spoken_input(text)['text'], text)
        self.assertTrue(identity_query_requested('御笠雪妃，我是谁'))
        self.assertEqual(binding_intent('雪妃，记住我，我叫汐蓝'), {'kind':'remember_self','name':'汐蓝'})
        self.assertEqual(parse_command('御笠雪妃，记住：名字是汐蓝')['value'], '汐蓝')

    def test_model_only_source_retains_caller_messages_and_no_persona_builder(self):
        path = ROOT/'aura/tools/model_inference_host.py'
        self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(),
                         'ace827aa21d9b6c404366677d05fc20054fe88f265af8ca0a20107e082cbf5c8')
        tree = ast.parse(path.read_text(encoding='utf-8'))
        method = next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == '_ollama')
        self.assertTrue(any(isinstance(n, ast.keyword) and n.arg == 'messages' and
            isinstance(n.value, ast.Subscript) and isinstance(n.value.value, ast.Name) and
            n.value.value.id == 'payload' for n in ast.walk(method)))
        self.assertFalse(any(isinstance(n, ast.Name) and n.id in
            ('fast_system_prompt','build_system_prompt','stream_body','selected_profile') for n in ast.walk(method)))
        legacy = ast.parse((ROOT/'aura/tools/dialogue_host_ollama.py').read_text(encoding='utf-8'))
        self.assertFalse(any(isinstance(n, ast.ImportFrom) and n.module in
            ('board.runtime.character','common.character_profile') for n in legacy.body))


if __name__ == '__main__':
    unittest.main(verbosity=2)
