"""Capabilities and loaded-source identity required by the wired launcher."""
import hashlib
from pathlib import Path

SERVICE_REVISION = 'voice-identity-gpu-20261030-r11'
CAPABILITIES = {'bounded_tts_requests': 1, 'correlated_worker_results': 1, 'cancel_owned_worker': 1, 'runtime_dependency_health': 1, 'owned_worker_lifetime': 1, 'authorized_profile_memory': 1, 'revocable_profile_grants': 1, 'audio_clock_animation': 1, 'audio_first_wake': 1, 'bounded_device_context': 1, 'timeline_memory': 1, 'background_memory_digests': 1, 'confirmed_transcript_deletion': 1, 'fact_revision_history': 1, 'natural_fact_answers': 1, 'memory_source_coverage': 1, 'queued_voice_admission': 1, 'bounded_voice_request_diagnostics': 1, 'request_input_fingerprint': 1, 'precise_timeline_voice_intent': 1, 'idle_tts_cuda_cache_release': 1, 'gpu_phase_coordination': 1, 'calibrated_gpu_admission': 1, 'cold_tts_capacity_preflight': 1, 'turn_speaker_observation': 1, 'optional_face_observation': 1, 'anonymous_speaker_timeline': 1, 'explicit_face_voice_binding': 1, 'original_gallery_revocation': 1}
SOURCE_FILES = (
    'board/runtime/audio/channel_jobs.py',
    'board/runtime/audio/face_binding_bridge.py',
    'board/runtime/audio/face_gallery_readback.py',
    'board/runtime/audio/omnivoice_voice.py',
    'board/runtime/audio/selected_voice.py',
    'board/runtime/audio/voice_channel.py',
    'common/anonymous_voice.py',
    'common/binding_api.py',
    'common/binding_intent.py',
    'common/conversation_context.py',
    'common/conversation_store.py',
    'common/device_memory.py',
    'common/device_policy.py',
    'common/face_binding_wire.py',
    'common/fact_answers.py',
    'common/gpu_coordination.py',
    'common/identity_links.py',
    'common/memory_commands.py',
    'common/memory_controls.py',
    'common/profile_access.py',
    'common/profile_memory.py',
    'common/profile_selection.py',
    'common/speaker_turns.py',
    'common/speaker_visual.py',
    'common/speech_motion.py',
    'common/spoken_input.py',
    'common/timeline.py',
    'common/timeline_config.py',
    'common/timeline_conversations.py',
    'common/timeline_observations.py',
    'common/timeline_summaries.py',
    'common/visual_question.py',
    'common/voice_admission.py',
    'common/voice_service_capabilities.py',
    'common/voice_wake.py',
    'config/anonymous_identity.local.json',
    'config/board_dialogue_model.json',
    'config/face_gallery_readback.local.json',
    'config/gpu_runtime.local.json',
    'config/ollama_runtime.local.json',
    'config/profile_access.local.json',
    'config/timeline_memory.json',
    'config/voice_latency.json',
    'tools/binding_dispatch.py',
    'tools/binding_hub_runtime.py',
    'tools/binding_identity_stream.py',
    'tools/binding_model_adapter.py',
    'tools/board_model_host.py',
    'tools/cuda_memory_stats.py',
    'tools/device_client.py',
    'tools/device_hub.py',
    'tools/dialogue_host_ollama.py',
    'tools/dialogue_stream.py',
    'tools/enrollment_receipts.py',
    'tools/identity_resolution.py',
    'tools/memory_timeline_host.py',
    'tools/owned_speech_process.py',
    'tools/private_gallery_reference.py',
    'tools/profile_cli.py',
    'tools/profile_control.py',
    'tools/progressive_speaker.py',
    'tools/progressive_speaker_hub.py',
    'tools/provisional_voice.py',
    'tools/selected_voice_service.py',
    'tools/service_instance_lock.py',
    'tools/social_feedback.py',
    'tools/speaker_capture_scope.py',
    'tools/speaker_conversation.py',
    'tools/speaker_device.py',
    'tools/speaker_turn_host.py',
    'tools/speaker_turns.py',
    'tools/thinking_feedback.py',
    'tools/unified_identity_binding.py',
    'tools/visual_question_host.py',
    'tools/visual_voice_host.py',
    'tools/voice_channel_source.py',
    'tools/voice_service_health.py',
    'tools/voice_startup_guard.py',
    'tools/voice_worker_transport.py',
)


def source_fingerprint(aura):
    digest = hashlib.sha256()
    for name in SOURCE_FILES:
        digest.update(name.encode('utf-8') + b'\0')
        digest.update(hashlib.sha256((Path(aura)/name).read_bytes()).digest())
    return digest.hexdigest()


def require_current_voice(health, model, fingerprint):
    if health.get('ready') is not True or health.get('voice_protocol') != 'aura-voice-1':
        raise ValueError('Voice service is not ready or has an incompatible protocol')
    if health.get('llm_model') != model:
        raise ValueError('Voice service model differs from configured model')
    if health.get('service_revision') != SERVICE_REVISION or health.get('source_fingerprint') != fingerprint:
        raise ValueError('Voice service source revision differs; controlled restart required')
    actual = health.get('capabilities', {})
    if not isinstance(actual, dict) or any(type(actual.get(k)) is not int or actual[k] < v for k, v in CAPABILITIES.items()):
        raise ValueError('Voice service is missing required reliability capabilities')
