"""Candidate constructor; original factory/profile/guide methods are inherited.
No runtime globals or main source are changed.
"""
from pathlib import Path
from tools.board_business_gui import (GuiBoardBusiness, BoardBusinessConfig,
    create_board_business_runtime, ConversationSelection, local_feedback_provider)
from tools.yuki_business_candidate import (bind_runtime_pair, load_private_face_readback,
    selected_feedback_provider, validate_feedback_character)

class ProductionGuiBoardBusiness(GuiBoardBusiness):
    def __init__(self, stage, value, aura):
        if not isinstance(value, dict) or value.get('enabled') is not True:
            raise ValueError('Board business must be explicitly enabled')
        required = {'enabled', 'private_root', 'utc_bounds', 'data_origin', 'asr_directory',
                    'frontend_directory', 'feedback_manifest', 'feedback_manifest_sha256', 'bootstrap_receipt', 'bootstrap_receipt_sha256'}
        optional = {'model_port', 'timeout_ms', 'timezone', 'entry_mode', 'asr_threads',
                    'frontend_threads', 'visual_device_id', 'speaker', 'face_readback',
                    'retention_enabled', 'resume_saved_conversation', 'frontend_optimization', 'capture_priority_nice', 'frontend_process'}
        if not required <= set(value) or set(value) - required - optional:
            raise ValueError('Invalid board business configuration')
        if value['data_origin'] != 'board' or type(value.get('retention_enabled',False)) is not bool:
            raise ValueError('Formal production requires explicit board origin and retention boolean')
        if type(value.get('resume_saved_conversation',True)) is not bool:
            raise ValueError('Choose saved anonymous continuation explicitly')
        from tools.production_frontend_selection import validate_frontend_options
        self.frontend_optimization,self.capture_priority_nice=validate_frontend_options(value)
        self.frontend_process=value.get('frontend_process',False)
        from common.board_production_bootstrap import verify_production_bootstrap
        verify_production_bootstrap(value['private_root'], value['bootstrap_receipt'], value['bootstrap_receipt_sha256'])
        import hashlib
        if hashlib.sha256(Path(value['feedback_manifest']).read_bytes()).hexdigest() != value['feedback_manifest_sha256']:
            raise ValueError('The selected public cue manifest changed')
        readback = load_private_face_readback(value.get('face_readback'))
        readback.verify(readback.config)
        from board.runtime.audio.board_asr import BoardParaformer
        from tools.production_frontend_selection import create_frontend_pool
        from board.runtime.audio.channel_jobs import ChannelConversationJobs
        from tools.profile_control import access_from_config
        self.character_pair = stage.character_pair
        if self.character_pair is None:
            raise ValueError("Explicit candidate pair required")
        self.face_readback_spec = value.get('face_readback')
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
        try:
            self.frontend = create_frontend_pool(value['frontend_directory'],optimization=self.frontend_optimization,
                                                num_threads=value.get('frontend_threads', 1),frontend_process=self.frontend_process)
            config = BoardBusinessConfig(value['private_root'], tuple(value['utc_bounds']),
                model_port=value.get('model_port', 8797), timeout_ms=value.get('timeout_ms', 120000),
                timezone=value.get('timezone', 'America/Los_Angeles'), entry_mode=value.get('entry_mode', 'voice_first'),
                data_origin=value['data_origin'], visual_device_id=value.get('visual_device_id', 'board-camera'),
                bootstrap_receipt=value['bootstrap_receipt'], bootstrap_receipt_sha256=value['bootstrap_receipt_sha256'],
                retention_enabled=value.get('retention_enabled',False))
            self.runtime = create_board_business_runtime(config, stage.board_boot_id,
                asr=asr, system_prompt=self.character_pair.selected_prompt,
                conversation_selection=ConversationSelection(Path(value['private_root'])/'conversation_selection.json'),
                identity_snapshot=lambda: stage.services.identity_snapshot() if stage.services is not None else None,
                identity_command=ChannelConversationJobs._identity_command,
                profile_access=access_from_config(aura), feedback_provider=feedback,
                capture_idle=self.capture_idle)
            from common.board_production_bootstrap import register_anonymous_conversation
            self.runtime.jobs.conversation_selection.before_publish = (
                lambda cid: register_anonymous_conversation(self.runtime.store, cid))
            bind_runtime_pair(self.runtime, self.character_pair)
            self.runtime.initialize_clock(timeout=3.)
            speaker = value.get('speaker')
            if speaker is not None:
                self._attach_speaker(speaker, stage.board_boot_id)
            elif value['data_origin'] == 'board':
                raise ValueError('The board-owned replacement requires the existing speaker/identity business')
            initialize_anonymous_selection(self.runtime, value.get('resume_saved_conversation',True))
            validate_feedback_character(feedback())
            self.runtime.jobs.prepare_feedback()
            self.runtime.jobs.feedback_provider = selected_feedback_provider(feedback, self.character_pair)
        except BaseException:
            self.close()
            raise


    def recording_options(self,visual_controller):
        if self.capture_priority_nice==0:
            return super().recording_options(visual_controller)
        from tools.production_frontend_selection import priority_recording_options
        return priority_recording_options(self,visual_controller)

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
        readback = load_private_face_readback(self.face_readback_spec)
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


    def close(self):
        # A lease close cancels one turn; only GUI shutdown retires this model child.
        pool=getattr(self,'frontend',None)
        shutdown=getattr(getattr(pool,'gate',None),'shutdown',None)
        if callable(shutdown):
            recording=getattr(self,'recording',None)
            if recording is not None and not self.worker_owned and not recording.closed:
                recording.close()
            pool.close()
            if not shutdown():
                raise RuntimeError('frontend_worker_shutdown_incomplete')
        return super().close()

    def activate(self):
        self.character_pair.require_ready()
        return super().activate()

def prepare_board_business(stage, value, aura):
    return ProductionGuiBoardBusiness(stage, value, aura)


def initialize_anonymous_selection(runtime, resume_saved):
    """Explicit root continuation policy; no profile/grant/token is imported."""
    import hashlib
    selection = runtime.jobs.conversation_selection
    proof = runtime.bootstrap_proof
    if resume_saved and proof.get('conversation_selection_verified') is True:
        raw = Path(selection.path).read_bytes()
        if hashlib.sha256(raw).hexdigest() != proof.get('conversation_selection_sha256'):
            raise ValueError('Verified anonymous conversation reference changed before admission')
        runtime.jobs.select_conversation(resume=True)
        runtime.initial_selection = dict(mode='saved_anonymous', session_is_fresh=True,
                                        profile_grant_imported=False)
    elif resume_saved and not proof.get('conversation_selection_verified'):
        runtime.jobs.select_conversation(resume=False)
        runtime.initial_selection = dict(mode='new_anonymous_no_saved_reference', session_is_fresh=True,
                                        profile_grant_imported=False)
    else:
        runtime.initial_selection = dict(mode='explicit_selection_required', session_is_fresh=True,
                                        profile_grant_imported=False)
