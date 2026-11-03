"""Explicit, board-local candidate pairing. Importing opens no device or store.

Only this independently packaged profile uses these adapters. Existing core,
permission, playback receipt, identity and memory implementations remain intact.
There is deliberately no live profile switch: rollback replaces the whole idle
candidate bundle, with its previous name/persona/renderer together.
"""
from dataclasses import dataclass
import hashlib
import json
import math
from pathlib import Path
import re
import threading
import types

PAIR_VERSION = 'xuefei-yuki-board-v1-candidate'
PAIR_CONFIG_SHA256 = '__PAIR_CONFIG_SHA256__'
PROFILE_ID = 'fuyukiss-yuki-freemote39-frame-mesh'
PROFILE_SHA256 = 'b7b71396c267db80a44c2b32df4ba53ded7920ac952b2fbbfebafba349f85f55'
NATIVE_PACKAGE_SHA256 = 'c0107904f8cd0b3e351666ade5fc7234e4278a82d165925dbbdc1459783baebb'


class PairRejected(ValueError):
    pass


def _read_pinned(root, relative, expected, maximum=32 * 1024 * 1024):
    relative = Path(relative)
    if relative.is_absolute() or '..' in relative.parts:
        raise PairRejected('Candidate resource must stay inside the reviewed bundle')
    path = root / relative
    if any(part.is_symlink() for part in (path, *path.parents) if part != root.parent):
        raise PairRejected('Candidate resource cannot use symlinks')
    path = path.resolve(strict=True)
    if not path.is_relative_to(root) or not path.is_file() or path.stat().st_size > maximum:
        raise PairRejected('Invalid candidate resource')
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != expected:
        raise PairRejected('Candidate resource fingerprint changed')
    return raw


class CharacterSpeechPolicy:
    """Exact reviewed addresses, without new ASR homophone assumptions.

    Raw transcription, quoted names, numbers and negation are never rewritten.
    Prefix removal is only a temporary intent-parser input; it is not a user
    event, identity name, permission, history edit or model-generated alias.
    """
    names = ('御笠雪妃', '雪妃')
    wake_words = names + ('欸', '哎')
    display_name = '雪妃'
    aliases = ()
    _punct = r'[\s，,。！？!?、：:]'
    _follow = r'(?:你|我|请|帮|陪|登记|记住|记得|长期记住|更正|忘记|查看|查询|清空|清除|删除|确认|取消|今天|现在|在吗|啊|呀)'
    _address = re.compile(
        r'^\s*(?:(?:你好[啊呀]?|嗨|嘿|喂|早上好|下午好|晚上好|早安|晚安)'
        + _punct + r'*)?(?:御笠雪妃|雪妃)(?=$|' + _punct + r'|' + _follow + r')')
    _legacy = re.compile(
        r'^\s*(?:(?:你好[啊呀]?|嗨|嘿|喂)' + _punct + r'*)?'
        r'(?:汐蓝|西兰|西蓝|溪蓝|希蓝|夕蓝|汐兰)(?=$|' + _punct + r'|' + _follow + r')')

    @staticmethod
    def prepare(text):
        if not isinstance(text, str):
            raise ValueError('Recognized speech must be text')
        return dict(raw_text=text, text=text, adjustments=[])

    def strip_address(self, text):
        if not isinstance(text, str):
            raise ValueError('Recognized speech must be text')
        match = self._address.match(text)
        if not match:
            return text
        return re.sub(r'^' + self._punct + r'+', '', text[match.end():]).strip()

    def legacy_vocative(self, text):
        return bool(isinstance(text, str) and self._legacy.match(text))

    def wake_request(self, text):
        from common.voice_wake import wake_request
        return wake_request(text, words=self.wake_words)


@dataclass(frozen=True)
class PairIdentity:
    profile_version: str
    display_name: str
    formal_name: str
    romanized_name: str
    render_profile_id: str
    render_source_profile_sha256: str
    persona_config_sha256: str
    prompt_sha256: str


class CandidatePair:
    def __init__(self, root, metadata, persona):
        self.root, self.metadata, self.persona = root, metadata, persona
        self.identity = PairIdentity(**metadata['identity'])
        self.speech = CharacterSpeechPolicy()
        self.lock = threading.RLock()
        self.mailbox = None
        self.state = 'PREPARED'
        self.failure = ''
        self.invalidators = []
        self._activate = None
        self._activation_called = False

    @property
    def selected_prompt(self):
        # Construction is permitted while the GL widget is unrealized; actual
        # jobs/context/commands all require the same ready pair before use.
        return self.persona.system_prompt

    @property
    def demo_lines(self):
        return (
            dict(id='greeting', label='雪妃问候', text='你好，我是雪妃。今天想聊些什么？', emotion='friendly', action=''),
            dict(id='happy', label='开心回应', text='太好了，又向前走了一步。我也有点开心。', emotion='happy', action=''),
            dict(id='gentle', label='轻声回应', text='先歇一会儿吧。你愿意说的话，我会认真听。', emotion='sad', action=''),
        )

    def attach_mailbox(self, mailbox):
        with self.lock:
            if self.mailbox is not None:
                raise PairRejected('One candidate pair owns exactly one native mailbox')
            self.mailbox = mailbox

    def on_ready(self, callback):
        with self.lock:
            if self._activate is not None or self._activation_called:
                raise PairRejected('Candidate startup activation is one-shot')
            self._activate = callback

    def observe_native_frame(self, stats):
        """Called only after the one local EGL widget successfully swaps.

        Source/profile hashes were validated locally before widget creation;
        frame metadata alone never authorizes an unrelated renderer or persona.
        This is readiness, not performance or visual-fidelity acceptance.
        """
        with self.lock:
            if self.state == 'FAILED' or self.mailbox is None:
                return
            if type(stats.get('frames')) is not int or stats['frames'] < 1:
                self.fail('invalid_native_readiness')
                return
            with self.mailbox.lock:
                self.mailbox._drawn = True
            self.state = 'READY'
            callback = None
            if self._activate is not None and not self._activation_called:
                self._activation_called = True
                callback = self._activate
        if callback is not None:
            try:
                callback()
            except BaseException:
                self.fail('business_activation_failed')
                raise

    def require_ready(self):
        from tools.board_persona_candidate import require_active_pair
        with self.lock:
            ready = self.state == 'READY' and self.mailbox is not None and self.mailbox.ready
            return require_active_pair(self.persona, profile_version=self.identity.profile_version,
                render_profile_id=self.identity.render_profile_id,
                render_source_profile_sha256=self.identity.render_source_profile_sha256,
                render_ready=ready)

    def ready_now(self):
        with self.lock:
            return self.state == 'READY' and self.mailbox is not None and self.mailbox.ready

    def fail(self, reason='native_unavailable'):
        with self.lock:
            first = self.state != 'FAILED'
            self.state = 'FAILED'
            if first:
                self.failure = str(reason)[:80]
            callbacks = tuple(self.invalidators) if first else ()
        # Never hold pair/GL/mailbox locks while cancelling the existing owners.
        for callback in callbacks:
            try:
                callback()
            except Exception:
                pass

    def status(self):
        with self.lock:
            return dict(profile_version=self.identity.profile_version,
                        display_name=self.identity.display_name, state=self.state,
                        selected=True, production_selected=False, fallback_allowed=False, target_fps=16,
                        render_profile_id=self.identity.render_profile_id,
                        render_source_profile_sha256=self.identity.render_source_profile_sha256,
                        prompt_sha256=self.identity.prompt_sha256, error=self.failure)


def prepare_pair(config, aura, source_hashes=None):
    """Validate only public local source/assets. No models, stores or devices."""
    value = config.get('character_pair')
    if value is None:
        if config.get('native_yuki', {}).get('enabled'):
            raise PairRejected('Native Yuki requires its atomic reviewed persona/name pair')
        return None
    if value != dict(enabled=True, profile_version=PAIR_VERSION,
                     selection='config/yuki_pair.candidate.json', selection_sha256=PAIR_CONFIG_SHA256):
        raise PairRejected('Select the exact explicit candidate pair')
    if config.get('board_business', {}).get('enabled') is not True:
        raise PairRejected('This candidate requires the existing board business factory')
    if config.get('portrait_offload', {}).get('enabled'):
        raise PairRejected('Candidate native renderer cannot coexist with portrait offload')
    if config.get('native_avatar') is not True or config.get('stable_avatar_fps') != 16:
        raise PairRejected('Candidate owns the only native sink at fixed16fps')
    root = Path(aura).resolve(strict=True)
    raw = _read_pinned(root, value['selection'], PAIR_CONFIG_SHA256, 65536)
    meta = json.loads(raw)
    if (meta['schema'] != 'aura.yuki.business_pair.v1' or
            meta['identity']['profile_version'] != PAIR_VERSION or
            meta['identity']['formal_name'] != '御笠雪妃' or
            meta['identity']['romanized_name'] != 'YUKI MIKASA' or
            meta['native_package_sha256'] != NATIVE_PACKAGE_SHA256 or
            meta['identity']['render_profile_id'] != PROFILE_ID or
            meta['identity']['render_source_profile_sha256'] != PROFILE_SHA256 or
            config.get('native_yuki') != meta['native_config']):
        raise PairRejected('Candidate renderer/persona configuration mismatch')
    for relative, expected in meta['runtime_pins'].items():
        _read_pinned(root, relative, expected)
    baseline = _read_pinned(root, 'config/yuki_accepted_prompt.baseline.txt',
                            meta['accepted_prompt_sha256'], 4096).decode('utf-8')
    from tools.board_persona_candidate import load_candidate
    persona = load_candidate((root/'config/persona.xuefei.candidate.json').resolve(strict=True),
        expected_config_sha256=meta['identity']['persona_config_sha256'],
        expected_profile_version=PAIR_VERSION, accepted_system_prompt=baseline)
    if hashlib.sha256(persona.system_prompt.encode()).hexdigest() != meta['identity']['prompt_sha256']:
        raise PairRejected('Candidate prompt fingerprint mismatch')
    if source_hashes is not None:
        source_hashes.update(meta['runtime_pins'])
        source_hashes[value['selection']] = PAIR_CONFIG_SHA256
    return CandidatePair(root, meta, persona)


def scoped_function(function, replacements):
    """A private globals dictionary; never mutates a shared imported module."""
    namespace = dict(function.__globals__)
    namespace.update(replacements)
    result = types.FunctionType(function.__code__, namespace, function.__name__,
                                function.__defaults__, function.__closure__)
    result.__kwdefaults__ = function.__kwdefaults__
    return result


def load_private_face_readback(spec):
    """Future publisher-supplied private metadata pin, with no stale fallback.

    This never opens the identity DB. The unchanged original readback performs
    its own boot/camera birth/source checks and only reads templates later in
    the existing authorized identity flow. No private configuration is bundled.
    """
    from board.runtime.audio.face_gallery_readback import FaceGalleryReadback
    if not isinstance(spec, dict) or set(spec) != {'path', 'sha256'}:
        raise PairRejected('Explicit fresh private face readback metadata pin required')
    path, expected = Path(spec['path']), spec['sha256']
    if (not path.is_absolute() or path.is_symlink() or not path.is_file()
            or path.stat().st_size > 65536 or not isinstance(expected, str)
            or re.fullmatch(r'[0-9a-f]{64}', expected) is None):
        raise PairRejected('Invalid explicit private readback metadata')
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != expected:
        raise PairRejected('Private face readback metadata fingerprint changed')
    return FaceGalleryReadback(json.loads(raw))


def validate_feedback_character(rows):
    if not isinstance(rows, dict):
        raise PairRejected('Approved public cue metadata required')
    for row in rows.values():
        text = row.get('reply_text', '')
        if not isinstance(text, str) or '汐蓝' in text:
            raise PairRejected('Approved public cue belongs to a different character')
    return rows


def selected_feedback_provider(provider, pair):
    """Never relabel or replay an old self-introduction as the new character.

    Existing reference transcripts/voice resources remain untouched. A cue
    with an old name needs a separately reviewed new cue, not text replacement.
    """
    def selected():
        pair.require_ready()
        return validate_feedback_character(provider())
    return selected


class PairedContextBuilder:
    def __init__(self, original, pair):
        self.original, self.pair = original, pair
        self.call = scoped_function(type(original).__call__, dict(prepare_spoken_input=pair.speech.prepare))
    def __call__(self, context, text, history=None):
        self.pair.require_ready()
        return self.call(self.original, context, text, history)
    def __getattr__(self, name):
        return getattr(self.original, name)


class PairedMemoryCommands:
    def __init__(self, original, pair):
        self.original, self.pair = original, pair
        self.call = scoped_function(type(original).__call__,
            dict(prepare_spoken_input=pair.speech.prepare, CHARACTER_NAME=pair.identity.display_name))
    def __call__(self, text, scope, **kwargs):
        self.pair.require_ready()
        if self.pair.speech.legacy_vocative(text):
            return None
        return self.call(self.original, self.pair.speech.strip_address(text), scope, **kwargs)


@dataclass(frozen=True)
class LocalRecordText:
    """Immutable request-local parsing text and verbatim recording input.

    The grant object is retained by identity; it is never copied, serialized,
    minted or sent to a model. No shared slot can be overwritten by a new job.
    """
    raw_record_text: str
    intent_text: str
    scope_items: tuple
    owner: object
    cancel_event: object

    @classmethod
    def capture(cls, job, text, speech):
        from common.model_inference_wire import Owner
        if not isinstance(text, str) or not 1 <= len(text) <= 4096 or '\x00' in text:
            raise PairRejected('Bounded original admitted text required')
        return cls(text, speech.strip_address(text), tuple(job.scope.items()),
                   Owner.from_dict(job.meta), job.cancelled)

    def same_scope(self, scope):
        if not isinstance(scope, dict):
            return False
        original = dict(self.scope_items)
        return (scope.keys() == original.keys() and
                all(scope[key] is value if key == 'grant' else scope[key] == value
                    for key, value in original.items()))


@dataclass(frozen=True)
class LocalRecordController:
    """Per-request proxy for exactly the two local recording entrypoints.

    Parsers/producers still consume intent_text. Only same-scope user_said is
    recorded from raw_record_text. Explicit device_event queries keep their
    intentionally normalized input, device scope, claims and original guards.
    Playback plans, stores, grants, clocks and receipts remain original objects.
    """
    original: object
    texts: LocalRecordText

    def __getattr__(self, name):
        return getattr(self.original, name)

    def _record_text(self, text, kwargs, input_source):
        owner = self.texts.owner
        if (self.original.board_boot_id != owner.board_boot_id or
                kwargs.get('session_id') != owner.session_id or
                kwargs.get('generation') != owner.generation or
                kwargs.get('turn_id') != owner.request_id or
                kwargs.get('cancel_event') is not self.texts.cancel_event):
            raise PairRejected('Local recording proxy belongs to another request')
        if input_source != 'user_said':
            return text
        scope = kwargs.get('scope')
        if not self.texts.same_scope(scope) or scope.get('kind') not in ('conversation', 'profile'):
            raise PairRejected('Raw user input cannot move to another or device scope')
        return self.texts.raw_record_text

    def prepare_local_sequence(self, text, producer, chunk_sink, **kwargs):
        return self.original.prepare_local_sequence(
            self._record_text(text, kwargs, 'user_said'), producer, chunk_sink, **kwargs)

    def prepare_local_reply(self, text, reply_factory, *, input_source='user_said', **kwargs):
        return self.original.prepare_local_reply(
            self._record_text(text, kwargs, input_source), reply_factory,
            input_source=input_source, **kwargs)


def bind_runtime_pair(runtime, pair):
    """Attach once before any worker starts, retaining the exact store/owners."""
    from tools import yuki_jobs_candidate
    if (runtime.started or runtime.closed or runtime.jobs.thread is not None or
            not runtime.controller.idle or hasattr(runtime.jobs, 'character_pair')):
        raise PairRejected('Pair only a fresh idle board business instance')
    builder, commands = runtime.controller.context_builder, runtime.controller.command_handler
    if builder.system_prompt != pair.selected_prompt:
        raise PairRejected('Factory prompt is not the selected atomic pair')
    new_builder = PairedContextBuilder(builder, pair)
    new_commands = PairedMemoryCommands(commands, pair)
    original_enabled, original_submit = runtime.jobs.enabled, runtime.jobs.submit
    def enabled():
        return pair.ready_now() and original_enabled()
    def submit(clip):
        pair.require_ready()
        return original_submit(clip)
    original_idle = runtime._foreground_idle
    def foreground_idle():
        return pair.ready_now() and original_idle()
    # All work below is metadata/method binding, before start(). No copied
    # queues, grants, scope, Store, profiles, identity guide or player owner.
    runtime.jobs.character_pair = pair
    runtime.jobs._admit_text = types.MethodType(yuki_jobs_candidate._admit_text, runtime.jobs)
    runtime.jobs._route = types.MethodType(yuki_jobs_candidate._route, runtime.jobs)
    runtime.jobs.enabled, runtime.jobs.submit = enabled, submit
    runtime._foreground_idle = foreground_idle
    runtime.controller.context_builder = new_builder
    runtime.controller.command_handler = new_commands
    pair.invalidators.append(runtime.jobs.cancel)
    runtime.character_pair = pair


class CandidateMonitorChoice:
    """This unselected candidate never resumes a persisted microphone choice.

    Future explicit operator toggles are RAM-only for this candidate process;
    the production preference file is neither read nor overwritten.
    """
    def __init__(self, pair):
        self.pair, self.enabled = pair, False
        pair.invalidators.append(lambda: self.write(False))
    def read(self):
        return self.enabled and self.pair.ready_now()
    def write(self, enabled):
        if type(enabled) is not bool:
            raise ValueError('Expected boolean monitoring choice')
        if enabled:
            self.pair.require_ready()
        self.enabled = enabled


class NumericFacials:
    """The original envelope values, without loading old eye/mouth/body PNGs."""
    def __init__(self, core, *, expressive_body=False):
        self.core = core
        self.envelope = self.closing = None
        self.last_gain = self.last_level = 0.
        self.last_asset = None
    def begin(self, envelope):
        self.envelope = envelope
        self.closing = None
        self.last_gain = self.last_level = 0.
    def stop(self, now):
        self.envelope = self.closing = None
        self.last_gain = self.last_level = 0.
    def values(self, audio_time, playing, now):
        from tools.facial_layers import interpolate
        if playing and self.envelope:
            return (interpolate(self.envelope['gains'], audio_time, self.envelope['hop_seconds']),
                    interpolate(self.envelope['levels'], audio_time, self.envelope['hop_seconds']))
        return 0., 0.
    def apply(self, *args):
        raise PairRejected('Old PNG composition is disabled for this selected native profile')


def create_native_core():
    from board.interaction.avatar_player import AvatarPlayer
    class NativeLogicCore(AvatarPlayer):
        # The same production FSM/generation/reply/burst policy, no legacy
        # asset preload/sequence/SOP/pixel evaluation or old body seed work.
        def pool(self, state):
            return ()
        def sequence(self, *args, **kwargs):
            raise PairRejected('Old PNG sequences are disabled for the candidate')
        def sop(self, *args, **kwargs):
            raise PairRejected('Old PNG motion tables are disabled for the candidate')
        def display_frame(self, *args, **kwargs):
            raise PairRejected('Native failure cannot fall back to old PNG rendering')
    return NativeLogicCore()


def native_controller_type():
    from tools.streaming_controller import StreamingController
    from tools.realtime_controller import RealtimeController
    init = scoped_function(RealtimeController.__init__, dict(RealtimeFacials=NumericFacials))
    class NativeStreamingController(StreamingController):
        def __init__(self, *args, **kwargs):
            self.stream = None
            self.completed_streams = []
            init(self, *args, **kwargs)
    # channel_event/tick/completion/pause/cancel are inherited byte-for-byte.
    return NativeStreamingController
