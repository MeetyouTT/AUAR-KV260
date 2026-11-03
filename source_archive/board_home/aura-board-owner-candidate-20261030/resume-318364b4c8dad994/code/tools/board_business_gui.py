"""Opt-in bridge for the fresh r3 GTK/recording owners; no legacy host business.

The caller must supply an explicit board_business configuration. The loader
does not discover/migrate a Windows database or authorize a personal profile.
No dependency is downloaded and no microphone/player is opened here.
"""
import hashlib
import json
from pathlib import Path

from board.runtime.board_business import BoardBusinessConfig, create_board_business_runtime
from common.conversation_selection import ConversationSelection
from common.voice_wire import MAX_WAV, wav_payload


def local_feedback_provider(manifest_path):
    path = Path(manifest_path)
    if not path.is_absolute() or path.is_symlink():
        raise ValueError('Use an explicit local approved cue manifest')
    value = json.loads(path.read_text(encoding='utf-8'))
    if not isinstance(value, dict) or set(value) != {'version', 'assets'} or value['version'] != 1:
        raise ValueError('Invalid local cue manifest')
    assets = value['assets']
    if not isinstance(assets, dict) or set(assets) - {'thinking', 'arrival', 'invitation'} or 'thinking' not in assets:
        raise ValueError('The approved selected-voice thinking cue is required')
    checked = {}
    for name, row in assets.items():
        if not isinstance(row, dict) or set(row) != {'path', 'metadata'}:
            raise ValueError('Invalid local cue entry')
        audio = Path(row['path'])
        if not audio.is_absolute() or audio.is_symlink() or not audio.is_file() or audio.stat().st_size > MAX_WAV:
            raise ValueError('Invalid local cue resource')
        meta = wav_payload(row['metadata'], audio.read_bytes())
        if meta['duration_seconds'] > 5:
            raise ValueError('Local cue is too long')
        checked[name] = dict(meta, path=str(audio))
    # Playback still uses the existing verified resource, not a new copy/cache.
    return lambda: {name: dict(row) for name, row in checked.items()}


class GuiBoardBusiness:
    def __init__(self, stage, value, aura):
        if not isinstance(value, dict) or value.get('enabled') is not True:
            raise ValueError('Board business must be explicitly enabled')
        required = {'enabled', 'private_root', 'utc_bounds', 'data_origin', 'asr_directory',
                    'frontend_directory', 'feedback_manifest'}
        optional = {'model_port', 'timeout_ms', 'timezone', 'entry_mode', 'asr_threads', 'visual_device_id', 'speaker'}
        if not required <= set(value) or set(value) - required - optional:
            raise ValueError('Invalid board business configuration')
        from board.runtime.audio.board_asr import BoardParaformer
        from board.runtime.audio.board_capture import BoardFrontendPool
        from board.runtime.audio.board_gtcrn_fft import BoardFftSpeechGate
        from board.runtime.audio.channel_jobs import ChannelConversationJobs
        from tools.dialogue_host_ollama import fast_system_prompt
        from common.device_policy import MODEL_HINT
        from tools.profile_control import access_from_config
        self.recording = None
        self.worker_owned = False
        self.frontend = None
        self.runtime = None
        # Pin the exact Paraformer tested on ARM; no replacement ASR model.
        asr = BoardParaformer(value['asr_directory'],
            model_sha256='f36a0433bcf096bd6d6f11b80a3ac8bed110bdca632fe0d731df8d1a84475945',
            tokens_sha256='59aba8873a2ed1e122c25fee421e25f283b63290efbde85c1f01a853d83cb6e6',
            num_threads=value.get('asr_threads', 2))
        feedback = local_feedback_provider(value['feedback_manifest'])
        self.frontend = BoardFrontendPool(BoardFftSpeechGate(value['frontend_directory'], num_threads=1))
        config = BoardBusinessConfig(value['private_root'], tuple(value['utc_bounds']),
            model_port=value.get('model_port', 8797), timeout_ms=value.get('timeout_ms', 120000),
            timezone=value.get('timezone', 'America/Los_Angeles'), entry_mode=value.get('entry_mode', 'voice_first'),
            data_origin=value['data_origin'], visual_device_id=value.get('visual_device_id', 'board-camera'))
        try:
            self.runtime = create_board_business_runtime(config, stage.board_boot_id,
                asr=asr, system_prompt=fast_system_prompt()+MODEL_HINT,
                conversation_selection=ConversationSelection(Path(value['private_root'])/'conversation_selection.json'),
                identity_snapshot=lambda: stage.services.identity_snapshot() if stage.services is not None else None,
                identity_command=ChannelConversationJobs._identity_command,
                profile_access=access_from_config(aura), feedback_provider=feedback,
                capture_idle=self.capture_idle)
            self.runtime.initialize_clock(timeout=3.)
            speaker = value.get('speaker')
            if speaker is not None:
                self._attach_speaker(speaker, stage.board_boot_id)
            elif value['data_origin'] == 'board':
                raise ValueError('The board-owned replacement requires the existing speaker/identity business')
            self.runtime.jobs.prepare_feedback()
        except BaseException:
            self.close()
            raise

    def _attach_speaker(self, value, boot_id):
        from board.runtime.audio.board_speaker_onnx import BoardEcapaOnnxEncoder
        from board.runtime.audio.face_gallery_readback import FaceGalleryReadback
        from board.runtime.board_speaker_business import BoardSpeakerBusiness
        from common.speaker_identity import voiced_pcm
        required = {'enabled', 'model_directory', 'manifest_sha256', 'expected_model_id', 'anonymous_config'}
        if not isinstance(value, dict) or set(value) != required or value['enabled'] is not True:
            raise ValueError('Explicit pinned local speaker business configuration is required')
        fingerprint = value['manifest_sha256']
        if not isinstance(fingerprint, str) or len(fingerprint) != 64 or any(c not in '0123456789abcdef' for c in fingerprint):
            raise ValueError('The original ECAPA export manifest must be pinned')
        readback = FaceGalleryReadback.configured()
        if readback is None:
            raise ValueError('Fresh local face-gallery source binding is required')
        readback.verify(readback.config)  # Metadata/source-only check, no template export.
        service = BoardSpeakerBusiness.create(Path(self.runtime.config.private_root)/'speaker',
            encoder_factory=lambda: BoardEcapaOnnxEncoder(value['model_directory'],
                        expected_manifest_sha256=fingerprint, threads=1),
            board_boot_id=boot_id, quality=voiced_pcm, expected_model_id=value['expected_model_id'],
            anonymous_config=value['anonymous_config'], wall_clock=self.runtime.timeline.event_time,
            clock=self.runtime.clock, data_origin=self.runtime.config.data_origin)
        try:
            self.runtime.attach_speaker_business(service, face_readback=readback)
        except BaseException:
            service.close()
            raise

    @property
    def jobs(self):
        return self.runtime.jobs

    def recording_options(self, visual_controller):
        from board.runtime.audio.board_capture import BoardAutomaticCapture
        return dict(audio_frontend=None,
            auto_capture_factory=lambda *args, **kwargs: BoardAutomaticCapture(*args,
                frontend_factory=self.frontend.acquire, **kwargs),
            barge_capture_factory=self.runtime.make_barge_capture_factory(visual_controller.output,
                lambda: getattr(visual_controller, 'reply', ''), self.frontend.acquire))

    def bind_recording(self, recording):
        if recording.transcriber is not self.jobs:
            raise ValueError('Recording owner is not bound to this board dialogue job queue')
        self.recording = recording
        return recording

    def capture_idle(self):
        recording = self.recording
        if recording is None or recording.closed:
            return False
        # Silent wake listening need not prevent all future memory work.
        # A real speech onset/ASR/playback promptly makes this false.
        if recording._playback_active():
            return False
        if getattr(recording, 'barge_capture', None) is not None:
            return False
        capture = getattr(recording, 'capture', None)
        if capture is not None:
            status = capture.snapshot()
            if status.get('state') == 'ERROR' or status.get('speech_active'):
                return False
        return recording.recording_state not in ('ERROR', 'STOPPING')

    def activate(self):
        if self.recording is None:
            raise RuntimeError('Bind the existing recording/player owner before activation')
        self.worker_owned = True
        self.runtime.start()

    def close(self):
        if self.recording is not None and not self.worker_owned and not self.recording.closed:
            # Initialization failed before AvatarRenderWorker took ownership.
            # Normal live cleanup first closes that worker on its owner thread.
            self.recording.close()
        if self.frontend is not None:
            self.frontend.close()
        if self.runtime is not None:
            self.runtime.close()


def prepare_board_business(stage, value, aura):
    return GuiBoardBusiness(stage, value, aura)
