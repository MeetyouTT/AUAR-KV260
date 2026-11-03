"""Explicit startup-only character selection, separate from user identities.

No model, database, device or service is opened. The selected public text is
for legacy dialogue callers only; model-only transport owns no persona.
Missing/invalid selection fails closed rather than restoring another name.
"""
from dataclasses import dataclass
from functools import lru_cache
import hashlib
import json
from pathlib import Path
import re


PROFILE_VERSION = 'xuefei-yuki-board-v1-candidate'
RENDER_PROFILE = 'fuyukiss-yuki-freemote39-frame-mesh'
RENDER_SHA256 = 'b7b71396c267db80a44c2b32df4ba53ded7920ac952b2fbbfebafba349f85f55'
PERSONA_SHA256 = '11b1b4d04c55ac110969fd5dd7ffb37f29b29bbc26d9c7906e454d4f69af654e'
PERSONA_CANDIDATE_SHA256 = '33d2dbb87348591da9e288bb9867a8e246fa63a955c071236eeeb24688e2d536'


class CharacterProfileError(ValueError):
    pass


@dataclass(frozen=True)
class CharacterProfile:
    profile_version: str
    display_name: str
    formal_name: str
    romanized_name: str
    description: str
    greeting: str
    address_names: tuple
    asr_aliases: tuple
    wake_words: tuple
    render_profile_id: str
    render_source_profile_sha256: str
    persona_full_prompt: str
    persona_prompt_sha256: str
    selection_sha256: str

    @property
    def legacy_fast_prompt(self):
        # Legacy stream_body appends this unchanged device instruction once.
        from common.device_policy import MODEL_HINT
        return self.persona_full_prompt[:-len(MODEL_HINT)]


def load_profile(path):
    """Read one explicit public selection; never discovers business state."""
    from common.device_policy import MODEL_HINT
    path = Path(path)
    if not path.is_absolute() or path.is_symlink() or not path.is_file() or path.stat().st_size > 8192:
        raise CharacterProfileError('Explicit regular character selection is required')
    raw = path.read_bytes()
    try:
        value = json.loads(raw)
    except (ValueError, UnicodeError):
        raise CharacterProfileError('Invalid character selection JSON') from None
    fields = {'schema', 'profile_version', 'display_name', 'formal_name', 'romanized_name',
              'description', 'greeting', 'address_names', 'asr_aliases', 'wake_words',
              'render_profile_id', 'render_source_profile_sha256', 'persona_full_prompt',
              'persona_prompt_sha256', 'persona_candidate_config_sha256'}
    if not isinstance(value, dict) or set(value) != fields or value['schema'] != 'aura.character-profile-1':
        raise CharacterProfileError('Character selection schema mismatch')
    expected = dict(profile_version=PROFILE_VERSION, display_name='雪妃', formal_name='御笠雪妃',
                    romanized_name='YUKI MIKASA', render_profile_id=RENDER_PROFILE,
                    render_source_profile_sha256=RENDER_SHA256,
                    persona_prompt_sha256=PERSONA_SHA256,
                    persona_candidate_config_sha256=PERSONA_CANDIDATE_SHA256,
                    address_names=['御笠雪妃', '雪妃'], asr_aliases=[],
                    wake_words=['御笠雪妃', '雪妃', '欸', '哎'])
    if any(value[key] != expected_value for key, expected_value in expected.items()):
        raise CharacterProfileError('Unreviewed character/persona/renderer pair')
    for key in ('description', 'greeting'):
        text = value[key]
        if (not isinstance(text, str) or not 1 <= len(text) <= 80 or
                '汐蓝' in text or any(ord(c) < 32 for c in text)):
            raise CharacterProfileError('Invalid selected character text')
    prompt = value['persona_full_prompt']
    if (not isinstance(prompt, str) or len(prompt.encode('utf-8')) != 978 or
            hashlib.sha256(prompt.encode('utf-8')).hexdigest() != PERSONA_SHA256 or
            not prompt.endswith(MODEL_HINT) or prompt.count(MODEL_HINT) != 1):
        raise CharacterProfileError('Authoritative978B persona changed')
    return CharacterProfile(**{key: tuple(value[key]) if key in ('address_names','asr_aliases','wake_words')
                              else value[key] for key in fields - {'schema','persona_candidate_config_sha256'}},
                            selection_sha256=hashlib.sha256(raw).hexdigest())


@lru_cache(maxsize=1)
def selected_profile():
    """One immutable selection per process; changes require controlled restart."""
    return load_profile(Path(__file__).resolve().parents[1]/'config/character_profile.local.json')


def strip_character_address(text):
    """Intent-only prefix removal. The original ASR/history remains unchanged."""
    if not isinstance(text, str):
        raise ValueError('Recognized speech must be text')
    names = '|'.join(re.escape(name) for name in selected_profile().address_names)
    return re.sub(r'^(?:' + names + r')[，,\s]*', '', text)
