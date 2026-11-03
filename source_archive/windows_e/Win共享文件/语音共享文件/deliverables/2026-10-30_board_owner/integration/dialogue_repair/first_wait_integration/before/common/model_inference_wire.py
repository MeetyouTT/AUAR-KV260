"""Versioned, bounded wire contract for board-owned model requests.

Only transport ownership lives here. Scope, identity, prompts, memory and reply
policy belong to the board. No helper in this module opens a file or a database.
"""
from __future__ import annotations

import base64
from dataclasses import dataclass
import hashlib
import re

PROTOCOL_VERSION = 1
MAX_BODY = 256 * 1024
MAX_RESPONSE = 8 * 1024 * 1024
MAX_PCM = 4 * 1024 * 1024
MAX_MESSAGES = 64
MAX_MESSAGE_BYTES = 96 * 1024
MAX_OUTPUT_BYTES = 96 * 1024
MAX_BUDGET_MS = 300_000
OWNER_FIELDS = frozenset(('request_id', 'board_boot_id', 'session_id', 'generation'))
_TOKEN = re.compile(r'^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$')


class WireError(ValueError):
    def __init__(self, code='invalid_request'):
        super().__init__(code)
        self.code = code


@dataclass(frozen=True)
class Owner:
    request_id: str
    board_boot_id: str
    session_id: str
    generation: int

    @classmethod
    def from_dict(cls, payload):
        if not isinstance(payload, dict):
            raise WireError()
        values = [payload.get(key) for key in ('request_id', 'board_boot_id', 'session_id')]
        if any(not isinstance(value, str) or not _TOKEN.fullmatch(value) for value in values):
            raise WireError('invalid_owner')
        generation = payload.get('generation')
        if type(generation) is not int or not 0 <= generation < 2 ** 53:
            raise WireError('invalid_owner')
        return cls(*values, generation)

    def as_dict(self):
        return dict(request_id=self.request_id, board_boot_id=self.board_boot_id,
                    session_id=self.session_id, generation=self.generation)

    @property
    def session_key(self):
        return self.board_boot_id, self.session_id


def _string(value, limit, *, nonempty=True):
    if not isinstance(value, str) or (nonempty and not value.strip()):
        raise WireError()
    try:
        encoded = value.encode('utf-8')
    except UnicodeError:
        raise WireError() from None
    if len(encoded) > limit or '\x00' in value:
        raise WireError('content_limit')
    return value


def validate_request(kind, payload):
    """Return an independent normalized dict; reject all unrecognized fields."""
    if kind not in ('llm', 'tts', 'cancel', 'warmup') or not isinstance(payload, dict):
        raise WireError()
    if type(payload.get('protocol_version')) is not int or payload['protocol_version'] != PROTOCOL_VERSION:
        raise WireError('protocol_version')
    owner = Owner.from_dict(payload)
    common = OWNER_FIELDS | {'protocol_version'}
    allowed = common | ({'task', 'messages', 'options', 'budget_ms'} if kind == 'llm'
                        else {'text', 'budget_ms'} if kind == 'tts'
                        else {'target', 'budget_ms'} if kind == 'warmup' else set())
    if set(payload) - allowed:
        raise WireError('unexpected_field')
    normalized = dict(protocol_version=PROTOCOL_VERSION, **owner.as_dict())
    if kind == 'cancel':
        return normalized
    budget = payload.get('budget_ms')
    if type(budget) is not int or not 1 <= budget <= MAX_BUDGET_MS:
        raise WireError('invalid_budget')
    normalized['budget_ms'] = budget
    if kind == 'warmup':
        if payload.get('target') != 'tts':
            raise WireError('invalid_warmup_target')
        normalized['target'] = 'tts'
        return normalized
    if kind == 'tts':
        text = _string(payload.get('text'), 1920)
        if len(text) > 240 or any(ord(char) < 32 for char in text):
            raise WireError('content_limit')
        normalized['text'] = text
        return normalized
    if payload.get('task') not in ('dialogue', 'summary'):
        raise WireError('invalid_task')
    messages = payload.get('messages')
    if not isinstance(messages, list) or not 1 <= len(messages) <= MAX_MESSAGES:
        raise WireError('invalid_messages')
    copied, size = [], 0
    for message in messages:
        if not isinstance(message, dict) or set(message) != {'role', 'content'}:
            raise WireError('invalid_messages')
        if message['role'] not in ('system', 'user', 'assistant'):
            raise WireError('invalid_messages')
        text = _string(message['content'], MAX_MESSAGE_BYTES)
        size += len(text.encode('utf-8'))
        copied.append(dict(role=message['role'], content=text))
    if size > MAX_MESSAGE_BYTES or not any(message['role'] == 'user' for message in copied):
        raise WireError('content_limit')
    options = payload.get('options', {})
    if not isinstance(options, dict) or set(options) - {'think', 'num_predict'}:
        raise WireError('invalid_options')
    if 'think' in options and type(options['think']) is not bool:
        raise WireError('invalid_options')
    if 'num_predict' in options and (type(options['num_predict']) is not int or not 1 <= options['num_predict'] <= 1024):
        raise WireError('invalid_options')
    normalized.update(task=payload['task'], messages=copied, options=dict(options))
    return normalized


def make_response(owner, *, result=None, error=None, retryable=False):
    if not isinstance(owner, Owner):
        owner = Owner.from_dict(owner)
    body = dict(protocol_version=PROTOCOL_VERSION, **owner.as_dict(), ok=error is None)
    if error is None:
        body['result'] = result if result is not None else {}
    else:
        body['error'] = dict(code=error, retryable=bool(retryable))
    return body


def audio_payload(pcm, sample_rate=24000):
    if not isinstance(pcm, bytes) or not pcm or len(pcm) % 2 or len(pcm) > MAX_PCM:
        raise WireError('invalid_audio')
    if type(sample_rate) is not int or not 8000 <= sample_rate <= 96000:
        raise WireError('invalid_audio')
    return dict(encoding='pcm_s16le', sample_rate=sample_rate, channels=1,
                samples=len(pcm) // 2, sha256=hashlib.sha256(pcm).hexdigest(),
                pcm_base64=base64.b64encode(pcm).decode('ascii'))


def decode_audio(audio):
    fields = {'encoding', 'sample_rate', 'channels', 'samples', 'sha256', 'pcm_base64'}
    if not isinstance(audio, dict) or set(audio) != fields:
        raise WireError('invalid_audio')
    if (audio['encoding'] != 'pcm_s16le' or type(audio['channels']) is not int or audio['channels'] != 1
            or type(audio['samples']) is not int or not 1 <= audio['samples'] <= MAX_PCM // 2
            or type(audio['sample_rate']) is not int or not 8000 <= audio['sample_rate'] <= 96000
            or not isinstance(audio['pcm_base64'], str)
            or len(audio['pcm_base64']) > (MAX_PCM + 2) // 3 * 4
            or not isinstance(audio['sha256'], str)):
        raise WireError('invalid_audio')
    try:
        pcm = base64.b64decode(audio['pcm_base64'], validate=True)
    except (ValueError, UnicodeError):
        raise WireError('invalid_audio') from None
    if (len(pcm) != audio['samples'] * 2 or len(pcm) > MAX_PCM
            or hashlib.sha256(pcm).hexdigest() != audio['sha256']):
        raise WireError('invalid_audio')
    return pcm, audio['sample_rate']


def validate_response(payload, expected_owner, kind):
    """Validate ownership before exposing model text or decoding any audio."""
    if not isinstance(expected_owner, Owner):
        expected_owner = Owner.from_dict(expected_owner)
    if (not isinstance(payload, dict) or type(payload.get('protocol_version')) is not int
            or payload['protocol_version'] != PROTOCOL_VERSION):
        raise WireError('protocol_version')
    if Owner.from_dict(payload) != expected_owner:
        raise WireError('owner_mismatch')
    base = OWNER_FIELDS | {'protocol_version', 'ok'}
    if type(payload.get('ok')) is not bool:
        raise WireError('invalid_response')
    if not payload['ok']:
        error = payload.get('error')
        if (set(payload) != base | {'error'} or not isinstance(error, dict)
                or set(error) != {'code', 'retryable'} or type(error['retryable']) is not bool
                or not isinstance(error['code'], str) or not _TOKEN.fullmatch(error['code'])):
            raise WireError('invalid_response')
        return payload
    if set(payload) != base | {'result'} or not isinstance(payload.get('result'), dict):
        raise WireError('invalid_response')
    result = payload['result']
    if kind == 'llm':
        if set(result) - {'text', 'metrics'}:
            raise WireError('invalid_response')
        _string(result.get('text'), MAX_OUTPUT_BYTES)
        if 'metrics' in result:
            allowed = {'prompt_eval_count', 'eval_count', 'load_duration_ms', 'prompt_eval_duration_ms',
                       'eval_duration_ms', 'total_duration_ms'}
            metrics = result['metrics']
            if (not isinstance(metrics, dict) or set(metrics) - allowed
                    or any(type(value) not in (int, float) or not 0 <= value < 1e15 for value in metrics.values())):
                raise WireError('invalid_response')
    elif kind == 'tts':
        if set(result) != {'audio'}:
            raise WireError('invalid_response')
        decode_audio(result['audio'])
    elif kind == 'cancel':
        if set(result) != {'cancelled', 'state'} or type(result['cancelled']) is not bool or result['state'] not in ('cancelled', 'completed'):
            raise WireError('invalid_response')
    elif kind == 'warmup':
        if (set(result) != {'target', 'ready', 'num_step', 'memory_only'}
                or result['target'] != 'tts' or result['ready'] is not True
                or type(result['num_step']) is not int or result['num_step'] != 16
                or result['memory_only'] is not True):
            raise WireError('invalid_response')
    else:
        raise WireError('invalid_response')
    return payload
