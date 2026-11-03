"""Startup-fixed image/persona pair for the ORIGINAL legacy business.
No factory/store/context/permission changes; no runtime global mutation.
"""
from dataclasses import dataclass
import hashlib
import json
import math
from pathlib import Path
import re
import threading
import types

PAIR_VERSION='xuefei-yuki-board-v1-candidate'
PAIR_CONFIG_SHA256='87ad6a1cc520538c7c47b6b52aa5e99c24446efdeb49b69cfe65f8872398f2b0'
PROFILE_ID='fuyukiss-yuki-freemote39-frame-mesh'
PROFILE_SHA256='b7b71396c267db80a44c2b32df4ba53ded7920ac952b2fbbfebafba349f85f55'
NATIVE_PACKAGE_SHA256='c0107904f8cd0b3e351666ade5fc7234e4278a82d165925dbbdc1459783baebb'

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
        from board.runtime.character import DEMO_LINES
        return DEMO_LINES

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
                        selected=True, production_selected=True, fallback_allowed=False, target_fps=16,
                        render_profile_id=self.identity.render_profile_id,
                        render_source_profile_sha256=self.identity.render_source_profile_sha256,
                        prompt_sha256=self.identity.prompt_sha256, error=self.failure)


def scoped_function(function, replacements):
    """A private globals dictionary; never mutates a shared imported module."""
    namespace = dict(function.__globals__)
    namespace.update(replacements)
    result = types.FunctionType(function.__code__, namespace, function.__name__,
                                function.__defaults__, function.__closure__)
    result.__kwdefaults__ = function.__kwdefaults__
    return result


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


def prepare_pair(config, aura, source_hashes=None):
    """Read only pinned public resources, retaining original legacy business."""
    value = config.get('character_pair')
    expected = dict(enabled=True, profile_version=PAIR_VERSION,
        selection='config/yuki_pair.formal.json', selection_sha256=PAIR_CONFIG_SHA256)
    if value != expected:
        raise PairRejected('Select the exact formal image/persona pair')
    if config.get('board_business', {}).get('enabled'):
        raise PairRejected('Formal image-only overlay must retain the original legacy business')
    if (config.get('portrait_offload', {}).get('enabled') or
            config.get('native_avatar') is not True or config.get('stable_avatar_fps') != 16 or
            not config.get('streaming_conversation') or not config.get('persistent_audio')):
        raise PairRejected('Formal image requires one native16 sink and unchanged streaming PCM controller')
    root = Path(aura).resolve(strict=True)
    from common.character_profile import selected_profile
    selected = selected_profile()
    if (selected.profile_version != PAIR_VERSION or selected.render_profile_id != PROFILE_ID or
            selected.render_source_profile_sha256 != PROFILE_SHA256 or
            selected.persona_prompt_sha256 != '11b1b4d04c55ac110969fd5dd7ffb37f29b29bbc26d9c7906e454d4f69af654e' or
            selected.selection_sha256 != '5dcac93339a56c549ef176e260b4ed7f01fdc3307059c53aa3784b7a382f09c3'):
        raise PairRejected('Shared selected profile is not this formal image/persona pair')
    old_runtime = '/home/root/aura-board-vision-20261030/06391079cfddb734-r3-ubuntu/runtime'
    paths = {key:old_runtime+'/avatar_'+key+'_settings.json' for key in ('user','transcription','conversation','service')}
    if config.get('formal_settings_paths') != paths or not all(Path(p).is_file() for p in paths.values()):
        raise PairRejected('Formal overlay must preserve four existing original settings files')
    if config.get('formal_stage_root') != old_runtime+'/deliverables/2026-10-06_xilan_live':
        raise PairRejected('Formal overlay must preserve the original public stage/cache root')
    raw = _read_pinned(root, value['selection'], PAIR_CONFIG_SHA256, 65536)
    meta = json.loads(raw)
    if (meta['schema'] != 'aura.yuki.formal_legacy_pair.v1' or
            meta['identity']['profile_version'] != PAIR_VERSION or
            meta['identity']['formal_name'] != '御笠雪妃' or
            meta['identity']['romanized_name'] != 'YUKI MIKASA' or
            meta['native_package_sha256'] != NATIVE_PACKAGE_SHA256 or
            meta['identity']['render_profile_id'] != PROFILE_ID or
            meta['identity']['render_source_profile_sha256'] != PROFILE_SHA256 or
            config.get('native_yuki') != meta['native_config']):
        raise PairRejected('Formal renderer/persona configuration mismatch')
    for relative, expected_hash in meta['runtime_pins'].items():
        _read_pinned(root, relative, expected_hash)
    baseline = _read_pinned(root, 'config/yuki_accepted_prompt.baseline.txt',
        meta['accepted_prompt_sha256'], 4096).decode('utf8')
    from tools.board_persona_candidate import load_candidate
    persona = load_candidate(root/'config/persona.xuefei.candidate.json',
        expected_config_sha256=meta['identity']['persona_config_sha256'],
        expected_profile_version=PAIR_VERSION, accepted_system_prompt=baseline)
    if hashlib.sha256(persona.system_prompt.encode()).hexdigest() != meta['identity']['prompt_sha256']:
        raise PairRejected('Formal persona fingerprint mismatch')
    if source_hashes is not None:
        source_hashes.update(meta['runtime_pins'])
        source_hashes[value['selection']] = PAIR_CONFIG_SHA256
    return CandidatePair(root, meta, persona)


def paired_recording_type(original, pair):
    """Private startup class; preserve old capture/permissions/ACK/PCM owners.

    The same controller keeps all audio and full-playback acknowledgements.
    Renderer failure cancels it through the existing worker; readiness also
    gates admission and local starts. Normal unmap is not a readiness failure.
    """
    class PairedRecording(original):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            # A formal image switch is not consent to open the microphone.
            # Do this before the AvatarRenderWorker is constructed, leaving
            # the existing settings file intact. Only a later explicit UI
            # toggle may resume the existing listening path.
            if hasattr(self, 'monitor_enabled'):
                self.monitor_enabled=False
                self.monitor_state='PAUSED'
                self.monitor_reason='EXPLICIT_START_REQUIRED'
        def _listen(self):
            pair.require_ready()
            return super()._listen()
        def record_start(self):
            pair.require_ready()
            return super().record_start()
        def conversation_start(self):
            pair.require_ready()
            return super().conversation_start()
        def handsfree_toggle(self):
            if not getattr(self, 'monitor_enabled', False):pair.require_ready()
            return super().handsfree_toggle()
        def _queue_transcription(self):
            pair.require_ready()
            return super()._queue_transcription()
        def submit(self, text, *args, **kwargs):
            pair.require_ready()
            # Old cached introductions must never be relabelled as Yuki. New
            # cue text has a new content key; old named cue audio is not reused.
            if not isinstance(text, str) or '汐蓝' in text:
                raise PairRejected('Selected cue belongs to another character')
            return super().submit(text, *args, **kwargs)
    return PairedRecording


def local_channel_jobs_type(spec, pair):
    """Only static cues differ; original network/identity/store/ACK work stays.

    The explicit pre-generated public cue files are never user dialogue data.
    No stale Windows self-introduction or renamed cached waveform is accepted.
    """
    from board.runtime.audio.channel_jobs import ChannelConversationJobs
    from common.voice_wire import wav_payload, MAX_WAV
    expected = dict(path='/home/root/aura-board-owner-candidate-20261030/xuefei-static-cues-8222c2a0ff30471a/feedback.json',
        sha256='143f6b2ea0de6afcfc1fc76178faa3de22d8fdd2bbbabc7965ddc7488ea786de')
    if spec != expected:raise PairRejected('Explicit selected public cue manifest required')
    path = Path(spec['path'])
    raw = path.read_bytes()
    if path.resolve() != path or len(raw)>65536 or hashlib.sha256(raw).hexdigest()!=spec['sha256']:
        raise PairRejected('Selected public cue manifest changed')
    values = json.loads(raw)
    if set(values)!= {'version','assets'} or values['version'] != 1 or set(values['assets']) != {'thinking','arrival','invitation'}:
        raise PairRejected('Selected public cue schema changed')
    assets = {}
    for name,row in values['assets'].items():
        target = Path(row['path'])
        if target.parent != path.parent or target.name != name+'.wav' or target.resolve()!=target:
            raise PairRejected('Selected public cue redirected')
        if target.stat().st_size>MAX_WAV:raise PairRejected('Selected public cue too large')
        meta=wav_payload(row['metadata'],target.read_bytes())
        if '汐蓝' in meta['reply_text'] or meta['duration_seconds']>5:
            raise PairRejected('Selected cue belongs to another character')
        assets[name]=dict(meta,path=str(target))
    class LocalCueChannelJobs(ChannelConversationJobs):
        def prepare_feedback(self, config):
            # Preserve the original SpeechJobs.import_generated path contract.
            # Only reviewed public static waveforms enter this public cache;
            # an old file is never renamed or overwritten with new cue text.
            import os
            import uuid
            selected={}
            for name, value in assets.items():
                target=self.feedback_root/(value['sha256']+'.wav')
                if not target.exists():
                    raw=Path(value['path']).read_bytes()
                    wav_payload(value,raw)
                    temporary=target.with_name(target.name+'.part-'+uuid.uuid4().hex)
                    try:
                        fd=os.open(str(temporary),os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
                        with os.fdopen(fd,'wb') as out:out.write(raw)
                        # Link publishes a complete file without replacing any
                        # existing key. A concurrent same-key publication is OK
                        # only after the full WAV hash check below.
                        try:os.link(str(temporary),str(target))
                        except FileExistsError:pass
                    finally:temporary.unlink(missing_ok=True)
                wav_payload(value,target.read_bytes())
                selected[name]=dict(value,path=str(target))
            self.feedback_assets={'thinking':selected['thinking']}
            self.social_assets={name:selected[name] for name in ('arrival','invitation')}
            self.feedback_address=(config['host'],config['port'])
            self.feedback_error=''
        def submit(self, clip):
            pair.require_ready()
            return super().submit(clip)
    return LocalCueChannelJobs
