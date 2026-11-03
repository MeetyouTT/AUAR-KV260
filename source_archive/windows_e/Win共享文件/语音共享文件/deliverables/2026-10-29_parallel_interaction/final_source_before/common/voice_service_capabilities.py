"""Capabilities and loaded-source identity required by the wired launcher."""
import hashlib
from pathlib import Path

SERVICE_REVISION = 'voice-speaker-gpu-20261029-r10'
CAPABILITIES = {'gpu_phase_coordination':1,'turn_speaker_observation':1,'optional_face_observation':1,'bounded_tts_requests': 1, 'correlated_worker_results': 1,
                'cancel_owned_worker': 1, 'runtime_dependency_health': 1,'owned_worker_lifetime':1,
                'authorized_profile_memory':1,'revocable_profile_grants':1,'audio_clock_animation':1,'audio_first_wake':1,'bounded_device_context':1,'timeline_memory':1,'background_memory_digests':1,'confirmed_transcript_deletion':1,'fact_revision_history':1,'natural_fact_answers':1,'memory_source_coverage':1,'queued_voice_admission':1,'bounded_voice_request_diagnostics':1,'request_input_fingerprint':1,'precise_timeline_voice_intent':1,'idle_tts_cuda_cache_release':1}
SOURCE_FILES = (
    'board/runtime/audio/channel_jobs.py',
    'common/gpu_coordination.py',
    'common/speaker_turns.py',
    'common/speaker_visual.py',
    'config/gpu_runtime.local.json',
    'tools/cuda_memory_stats.py',
    'tools/device_hub.py',
    'tools/dialogue_host_ollama.py',
    'tools/speaker_capture_scope.py',
    'tools/speaker_conversation.py',
    'tools/speaker_device.py',
    'tools/speaker_turn_host.py',
    'tools/speaker_turns.py',
    'common/voice_admission.py',
    'common/fact_answers.py',
    'common/memory_controls.py',
    'common/timeline_summaries.py',
    'common/timeline.py','common/timeline_config.py','common/timeline_conversations.py',
    'common/timeline_observations.py','tools/memory_timeline_host.py','config/timeline_memory.json',
    'common/spoken_input.py',
    'common/device_policy.py',
    'common/voice_wake.py','common/device_memory.py','tools/device_client.py','tools/social_feedback.py',
    'tools/visual_voice_host.py','tools/visual_question_host.py','common/visual_question.py',
    'tools/board_model_host.py', 'tools/voice_channel_source.py',
    'tools/selected_voice_service.py', 'tools/voice_worker_transport.py','tools/owned_speech_process.py',
    'tools/voice_service_health.py', 'tools/dialogue_stream.py',
    'common/voice_service_capabilities.py', 'common/conversation_store.py',
    'common/conversation_context.py', 'common/memory_commands.py',
    'common/profile_access.py','common/profile_memory.py','tools/profile_control.py','tools/profile_cli.py',
    'config/profile_access.local.json','board/runtime/audio/voice_channel.py',
    'common/profile_selection.py',
    'common/speech_motion.py',
    'board/runtime/audio/omnivoice_voice.py', 'board/runtime/audio/selected_voice.py',
    'config/board_dialogue_model.json', 'config/voice_latency.json',
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
