"""Capabilities and loaded-source identity required by the wired launcher."""
import hashlib
from pathlib import Path

SERVICE_REVISION = 'voice-profile-memory-20261026-r2'
CAPABILITIES = {'bounded_tts_requests': 1, 'correlated_worker_results': 1,
                'cancel_owned_worker': 1, 'runtime_dependency_health': 1,'owned_worker_lifetime':1,
                'authorized_profile_memory':1,'revocable_profile_grants':1}
SOURCE_FILES = (
    'tools/board_model_host.py', 'tools/voice_channel_source.py',
    'tools/selected_voice_service.py', 'tools/voice_worker_transport.py','tools/owned_speech_process.py',
    'tools/voice_service_health.py', 'tools/dialogue_stream.py',
    'common/voice_service_capabilities.py', 'common/conversation_store.py',
    'common/conversation_context.py', 'common/memory_commands.py',
    'common/profile_access.py','common/profile_memory.py','tools/profile_control.py','tools/profile_cli.py',
    'config/profile_access.local.json','board/runtime/audio/voice_channel.py',
    'common/profile_selection.py',
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
