"""Full factory calls with public temporary files and fake models/services only."""
import ast
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
REPAIR = ROOT.parent
COMPONENT = 'tools/production_board_business_gui.py'
BASELINE = ('f36a0433bcf096bd6d6f11b80a3ac8bed110bdca632fe0d731df8d1a84475945',
            '59aba8873a2ed1e122c25fee421e25f283b63290efbde85c1f01a853d83cb6e6')
SMALL = ('3ef6c19369b912f7caf3cef8e545c5ccd1a33d9d7ec792a46668dc41c4b229ec',
         '4b2d964e18b9cf139b473003b6698fb2ed9a2a5ec55b93daa677b28f578897aa')


def module(name):
    return types.ModuleType(name)


class Fixture:
    def __init__(self, *, failure=None):
        self.failure = failure
        self.events = []
        self.asr_calls = []
        self.frontend_calls = []
        self.pool = self.runtime = None
        self.base_closes = 0
        self.artifacts = {'/public/baseline': BASELINE, '/public/small': SMALL}

    def modules(self):
        owner = self
        modules = {}
        for name in ('tools', 'common', 'board', 'board.runtime', 'board.runtime.audio'):
            value = module(name); value.__path__ = []; modules[name] = value
        gui = module('tools.board_business_gui')

        class Base:
            def capture_idle(self):
                return True

            def close(self):
                owner.base_closes += 1
                if self.frontend is not None:
                    self.frontend.close()
                if self.runtime is not None:
                    self.runtime.close()

        gui.GuiBoardBusiness = Base
        gui.BoardBusinessConfig = lambda *a, **kw: types.SimpleNamespace(args=a, **kw)
        gui.ConversationSelection = lambda path: types.SimpleNamespace(path=path)
        gui.local_feedback_provider = lambda path: lambda: {'thinking': 'public-fixture'}

        def runtime(config, boot, **kwargs):
            owner.events.append('runtime')
            if owner.failure == 'runtime':
                raise RuntimeError('public runtime failure')
            value = types.SimpleNamespace(config=config, jobs=types.SimpleNamespace(
                conversation_selection=types.SimpleNamespace(before_publish=None),
                prepare_feedback=lambda: owner.events.append('feedback')), store=object(),
                bootstrap_proof={}, asr=kwargs['asr'], closed=False, close_calls=0)

            def close():
                value.close_calls += 1; value.closed = True

            def clock(**kwargs):
                owner.events.append('clock')
                if owner.failure == 'clock':
                    raise RuntimeError('public clock failure')

            value.close, value.initialize_clock = close, clock
            owner.runtime = value
            return value

        gui.create_board_business_runtime = runtime
        modules[gui.__name__] = gui
        yuki = module('tools.yuki_business_candidate')
        yuki.bind_runtime_pair = lambda *a: owner.events.append('pair')
        yuki.load_private_face_readback = lambda *a: types.SimpleNamespace(
            config={}, verify=lambda *a: owner.events.append('face_metadata'))
        yuki.validate_feedback_character = lambda *a: None
        yuki.selected_feedback_provider = lambda feedback, pair: feedback
        modules[yuki.__name__] = yuki
        bootstrap = module('common.board_production_bootstrap')
        bootstrap.verify_production_bootstrap = lambda *a: owner.events.append('bootstrap')
        bootstrap.register_anonymous_conversation = lambda *a: None
        modules[bootstrap.__name__] = bootstrap
        asr = module('board.runtime.audio.board_asr')

        def make_asr(directory, **kwargs):
            owner.events.append('asr')
            owner.asr_calls.append((directory, dict(kwargs)))
            # Fake artifact admission: verifies the actual pair selected by the
            # full production constructor. No resource/model is loaded.
            expected = owner.artifacts.get(directory)
            actual = (kwargs['model_sha256'], kwargs['tokens_sha256'])
            if expected is None or actual != expected or owner.failure == 'asr':
                raise ValueError('public model or tokens pin mismatch')
            return types.SimpleNamespace(model_sha256=actual[0], tokens_sha256=actual[1],
                                         num_threads=kwargs['num_threads'])

        asr.BoardParaformer = make_asr
        modules[asr.__name__] = asr
        front = module('tools.production_frontend_selection')
        front.validate_frontend_options = lambda value: ('combined', -10)

        def frontend(directory, **kwargs):
            owner.events.append('frontend')
            owner.frontend_calls.append((directory, dict(kwargs)))
            if owner.failure == 'frontend':
                raise RuntimeError('public frontend construction failure')
            pool = types.SimpleNamespace(close_calls=0, shutdown_calls=0)
            def close():
                pool.close_calls += 1
            def shutdown():
                pool.shutdown_calls += 1
                return True
            pool.close = close
            pool.gate = types.SimpleNamespace(shutdown=shutdown)
            owner.pool = pool
            return pool

        front.create_frontend_pool = frontend
        modules[front.__name__] = front
        output = module('tools.production_output_format')
        def validate(mode):
            if mode not in ('json', 'dialogue_abc_v1'):
                raise ValueError('invalid public output format')
            return mode
        def install(runtime, **kwargs):
            owner.events.append('output')
            if owner.failure == 'output':
                raise RuntimeError('public output binding failure')
            return dict(kwargs)
        output.validate_dialogue_output_format, output.install_dialogue_output = validate, install
        modules[output.__name__] = output
        channel = module('board.runtime.audio.channel_jobs')
        channel.ChannelConversationJobs = types.SimpleNamespace(_identity_command=None)
        modules[channel.__name__] = channel
        profile = module('tools.profile_control')
        profile.access_from_config = lambda *a: object()
        modules[profile.__name__] = profile
        return modules

    def context(self):
        return patch.dict(sys.modules, self.modules())

    def load(self, branch='after'):
        name = '_public_small_factory_' + branch
        spec = importlib.util.spec_from_file_location(name, ROOT / branch / COMPONENT)
        chosen = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(chosen)
        def speaker(*args):
            self.events.append('speaker')
            if self.failure == 'speaker':
                raise RuntimeError('public speaker initialization failure')
        chosen.ProductionGuiBoardBusiness._attach_speaker = speaker
        return chosen

    def value(self, directory):
        cue = directory / 'public_feedback.json'; cue.write_bytes(b'{}')
        self.preference = directory / 'listening_preference.json'
        self.preference.write_bytes(b'{"enabled":false}\n')
        return dict(enabled=True, private_root=str(directory), utc_bounds=[0, 1], data_origin='board',
                    asr_directory='/public/baseline', frontend_directory='/public/frontend',
                    feedback_manifest=str(cue), feedback_manifest_sha256=hashlib.sha256(b'{}').hexdigest(),
                    bootstrap_receipt='/not-read', bootstrap_receipt_sha256='a'*64,
                    speaker={}, resume_saved_conversation=False, asr_threads=3,
                    frontend_threads=1, frontend_process=True, frontend_capture_process=True,
                    frontend_optimization='combined', capture_priority_nice=-10,
                    dialogue_output_format='dialogue_abc_v1')

    @staticmethod
    def stage():
        return types.SimpleNamespace(character_pair=types.SimpleNamespace(
            selected_prompt='公开固定配对人格'), board_boot_id='public-boot', services=None)


class SelectorTests(unittest.TestCase):
    def test_default_baseline_matches_existing_factory_arguments(self):
        observed = []
        for branch in ('before', 'after'):
            fixture = Fixture()
            with fixture.context(), tempfile.TemporaryDirectory() as temp:
                chosen = fixture.load(branch); value = fixture.value(Path(temp))
                product = chosen.prepare_board_business(fixture.stage(), value, None)
                observed.append((fixture.asr_calls, fixture.frontend_calls, product.dialogue_output))
                if branch == 'after':
                    self.assertEqual(product.asr_variant, 'baseline')
                self.assertEqual(product.runtime.asr.num_threads, 3)
                product.close()
        self.assertEqual(observed[0], observed[1])

    def test_small_uses_reviewed_pair_and_keeps_explicit_directory_threads_and_dialogue(self):
        fixture = Fixture()
        with fixture.context(), tempfile.TemporaryDirectory() as temp:
            chosen = fixture.load(); value = fixture.value(Path(temp))
            value.update(asr_variant='paraformer_small', asr_directory='/public/small')
            original = dict(value)
            product = chosen.prepare_board_business(fixture.stage(), value, None)
            self.assertEqual(fixture.asr_calls, [('/public/small', dict(
                model_sha256=SMALL[0], tokens_sha256=SMALL[1], num_threads=3))])
            self.assertEqual(product.asr_variant, 'paraformer_small')
            self.assertEqual(value, original)
            self.assertEqual(product.dialogue_output['mode'], 'dialogue_abc_v1')
            self.assertEqual(product.runtime.asr.num_threads, 3)
            self.assertEqual(fixture.frontend_calls[0][1], dict(
                optimization='combined', num_threads=1, frontend_process=True))
            self.assertEqual(fixture.preference.read_bytes(), b'{"enabled":false}\n')
            product.close()
            self.assertEqual(fixture.preference.read_bytes(), b'{"enabled":false}\n')

    def test_explicit_baseline_keeps_original_pair_and_default_threads(self):
        fixture = Fixture()
        with fixture.context(), tempfile.TemporaryDirectory() as temp:
            chosen = fixture.load(); value = fixture.value(Path(temp))
            value['asr_variant'] = 'baseline'; value.pop('asr_threads')
            product = chosen.prepare_board_business(fixture.stage(), value, None)
            self.assertEqual(fixture.asr_calls[0][1], dict(
                model_sha256=BASELINE[0], tokens_sha256=BASELINE[1], num_threads=2))
            product.close()

    def test_unknown_or_wrong_type_selector_refuses_before_private_or_model_construction(self):
        for bad in ('', 'small', 'BASELINE', 'paraformer-small', None, True, 0, [], {}, b'baseline'):
            with self.subTest(selector=repr(bad)):
                fixture = Fixture()
                with fixture.context(), tempfile.TemporaryDirectory() as temp:
                    chosen = fixture.load(); value = fixture.value(Path(temp)); value['asr_variant'] = bad
                    with self.assertRaises(ValueError):
                        chosen.prepare_board_business(fixture.stage(), value, None)
                    self.assertEqual(fixture.events, [])

    def test_wrong_directory_or_mixed_artifact_pair_never_falls_back(self):
        for variant, directory, artifact in (
                ('paraformer_small', '/public/baseline', BASELINE),
                ('baseline', '/public/small', SMALL),
                ('paraformer_small', '/public/mixed', (SMALL[0], BASELINE[1])),
                ('paraformer_small', '/public/mixed', (BASELINE[0], SMALL[1]))):
            with self.subTest(variant=variant, directory=directory, artifact=artifact):
                fixture = Fixture(); fixture.artifacts[directory] = artifact
                with fixture.context(), tempfile.TemporaryDirectory() as temp:
                    chosen = fixture.load(); value = fixture.value(Path(temp))
                    value.update(asr_variant=variant, asr_directory=directory)
                    with self.assertRaises(ValueError):
                        chosen.prepare_board_business(fixture.stage(), value, None)
                    self.assertEqual(len(fixture.asr_calls), 1)
                    self.assertEqual(fixture.frontend_calls, [])
                    self.assertEqual(fixture.base_closes, 0)  # Nothing later was constructed.

    def test_unreviewed_model_or_token_config_keys_rejected(self):
        for key in ('model_sha256', 'tokens_sha256', 'asr_model_sha256', 'asr_tokens_sha256'):
            with self.subTest(key=key):
                fixture = Fixture()
                with fixture.context(), tempfile.TemporaryDirectory() as temp:
                    chosen = fixture.load(); value = fixture.value(Path(temp)); value[key] = 'f'*64
                    with self.assertRaises(ValueError):
                        chosen.prepare_board_business(fixture.stage(), value, None)
                    self.assertEqual(fixture.events, [])

    def test_downstream_failures_keep_original_pool_shutdown_and_runtime_cleanup(self):
        for failure in ('frontend', 'runtime', 'clock', 'output', 'speaker'):
            with self.subTest(failure=failure):
                fixture = Fixture(failure=failure)
                with fixture.context(), tempfile.TemporaryDirectory() as temp:
                    chosen = fixture.load(); value = fixture.value(Path(temp))
                    value.update(asr_variant='paraformer_small', asr_directory='/public/small')
                    with self.assertRaises(RuntimeError):
                        chosen.prepare_board_business(fixture.stage(), value, None)
                    self.assertEqual(fixture.base_closes, 1)
                    if fixture.pool is not None:
                        self.assertEqual(fixture.pool.shutdown_calls, 1)
                        self.assertEqual(fixture.pool.close_calls, 2)
                    if fixture.runtime is not None:
                        self.assertEqual(fixture.runtime.close_calls, 1)
                    self.assertEqual(fixture.preference.read_bytes(), b'{"enabled":false}\n')

    def test_exact_live_before_and_model_algorithm_pins_python39_syntax(self):
        fresh = json.loads((REPAIR/'paraformer_small_validation/PRODUCTION_SOURCE_CHECK.json').read_text('utf-8'))
        self.assertEqual(hashlib.sha256((ROOT/'before'/COMPONENT).read_bytes()).hexdigest(),
                         fresh['source_pins'][COMPONENT])
        model = REPAIR/'first_wait_asr_candidate/before/board/runtime/audio/board_asr.py'
        self.assertEqual(hashlib.sha256(model.read_bytes()).hexdigest(),
                         fresh['source_pins']['board/runtime/audio/board_asr.py'])
        ast.parse((ROOT/'after'/COMPONENT).read_text('utf-8'), feature_version=(3, 9))


if __name__ == '__main__':
    unittest.main(verbosity=2)
