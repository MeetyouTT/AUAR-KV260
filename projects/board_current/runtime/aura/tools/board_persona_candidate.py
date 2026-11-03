"""Explicit board-side persona candidate; no defaults, devices or model calls.

This module only validates a reviewed text/config pair. The deployment owner
must call require_active_pair with the actual selected/ready render profile
before using the prompt, and restore the previous persona on render rollback.
No identity/profile key, speech alias, memory record or permission is changed.
"""
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import re


SCHEMA = 'aura.board.persona.candidate.v1'
BASELINE_SHA256 = 'ee62d5bacde4e3060dc53142191395c5b2abf766e08e147be991cbd857838a6b'
BASELINE_BYTES = 1032
REPLY_INSTRUCTION = ('输出JSON：reply_text为说出口的话，emotion为neutral/friendly/happy/sad之一，'
                     'avatar_action为空字符串。')
REPLY_CONTRACT = {
    'fields': ['reply_text', 'emotion', 'avatar_action'],
    'emotions': ['neutral', 'friendly', 'happy', 'sad'],
    'avatar_actions': [''],
    'prompt_target_max_characters': 48,
    'existing_validator_min_characters': 1,
    'existing_validator_max_characters': 500,
}
_DIGEST = re.compile(r'[0-9a-f]{64}\Z')
_VERSION = re.compile(r'[a-z0-9][a-z0-9_.-]{0,95}\Z')


class PersonaCandidateRejected(ValueError):
    pass


def _digest(value):
    if not isinstance(value, str) or not _DIGEST.fullmatch(value):
        raise PersonaCandidateRejected('Explicit lowercase SHA256 required')
    return value


@dataclass(frozen=True)
class BoardPersonaCandidate:
    profile_version: str
    display_name: str
    config_sha256: str
    render_profile_id: str
    render_source_profile_sha256: str
    system_prompt: str


def load_candidate(config_path, *, expected_config_sha256, expected_profile_version,
                   accepted_system_prompt):
    """Read one explicitly pinned public config, without activating anything.

    accepted_system_prompt comes from the caller's still-accepted board prompt;
    this candidate never imports a Windows model host or discovers a config.
    """
    from common.device_policy import MODEL_HINT
    from common.spoken_input import SPEECH_INPUT_HINT

    if not isinstance(accepted_system_prompt, str):
        raise PersonaCandidateRejected('Accepted board prompt is required')
    old = accepted_system_prompt.encode('utf-8')
    if len(old) != BASELINE_BYTES or hashlib.sha256(old).hexdigest() != BASELINE_SHA256:
        raise PersonaCandidateRejected('Accepted persona baseline changed; review the candidate again')
    if not isinstance(expected_profile_version, str) or not _VERSION.fullmatch(expected_profile_version):
        raise PersonaCandidateRejected('Explicit paired profile version required')
    path = Path(config_path)
    if not path.is_absolute() or path.is_symlink():
        raise PersonaCandidateRejected('Use an explicit regular candidate config')
    raw = path.read_bytes()
    if len(raw) > 8192 or hashlib.sha256(raw).hexdigest() != _digest(expected_config_sha256):
        raise PersonaCandidateRejected('Reviewed persona config fingerprint mismatch')
    try:
        value = json.loads(raw)
    except (ValueError, UnicodeError):
        raise PersonaCandidateRejected('Invalid candidate JSON') from None
    required = {'schema', 'profile_version', 'display_name', 'prompt_prefix',
                'render_profile_id', 'render_source_profile_sha256',
                'accepted_prompt_sha256', 'max_prompt_utf8_bytes', 'reply_contract'}
    if not isinstance(value, dict) or set(value) != required or value['schema'] != SCHEMA:
        raise PersonaCandidateRejected('Candidate config schema mismatch')
    if value['profile_version'] != expected_profile_version:
        raise PersonaCandidateRejected('Persona and selected bundle versions differ')
    if (value['accepted_prompt_sha256'] != BASELINE_SHA256 or
            type(value['max_prompt_utf8_bytes']) is not int or
            value['max_prompt_utf8_bytes'] != BASELINE_BYTES or
            json.dumps(value['reply_contract'], sort_keys=True, ensure_ascii=False) !=
            json.dumps(REPLY_CONTRACT, sort_keys=True, ensure_ascii=False)):
        raise PersonaCandidateRejected('Existing prompt/reply contract changed')
    name, prefix = value['display_name'], value['prompt_prefix']
    if (not isinstance(name, str) or not 1 <= len(name) <= 12 or
            not isinstance(prefix, str) or name not in prefix or
            any(ord(char) < 32 for char in name + prefix)):
        raise PersonaCandidateRejected('Invalid reviewed character text')
    render_profile = value['render_profile_id']
    if not isinstance(render_profile, str) or not _VERSION.fullmatch(render_profile):
        raise PersonaCandidateRejected('Explicit render source profile required')
    render_sha = _digest(value['render_source_profile_sha256'])
    # Both existing interpretation/device safeguards stay byte-for-byte intact.
    prompt = prefix + SPEECH_INPUT_HINT + REPLY_INSTRUCTION + MODEL_HINT
    if len(prompt.encode('utf-8')) > BASELINE_BYTES:
        raise PersonaCandidateRejected('Candidate exceeds the accepted UTF8 prompt budget')
    return BoardPersonaCandidate(expected_profile_version, name,
                                 hashlib.sha256(raw).hexdigest(), render_profile,
                                 render_sha, prompt)


def require_active_pair(candidate, *, profile_version, render_profile_id,
                        render_source_profile_sha256, render_ready):
    """Refuse persona/image disagreement, including renderer failure/fallback.

    These arguments must be actual local renderer state, not model output or
    identity observations. This validates metadata; it does not verify GPU work.
    """
    if not isinstance(candidate, BoardPersonaCandidate):
        raise PersonaCandidateRejected('Validated board candidate required')
    if (render_ready is not True or profile_version != candidate.profile_version or
            render_profile_id != candidate.render_profile_id or
            render_source_profile_sha256 != candidate.render_source_profile_sha256):
        raise PersonaCandidateRejected('Persona/render pair is not the same ready profile; restore the previous pair')
    return candidate.system_prompt
