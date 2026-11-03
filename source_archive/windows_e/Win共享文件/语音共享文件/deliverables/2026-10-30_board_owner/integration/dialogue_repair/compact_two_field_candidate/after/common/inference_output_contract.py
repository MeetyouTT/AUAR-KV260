"""Caller-selected inference formats and metadata; no business state or IO.

Only complete model responses are returned. No fragment authorizes speech.
"""
from __future__ import annotations

import copy
import json
import math


FORMATS = frozenset({'json', 'dialogue_schema_v1', 'dialogue_abc_v1', 'dialogue_ab_v1'})
FIELDS = {'a': 'reply_text', 'b': 'emotion', 'c': 'avatar_action'}
EXTRA_METRICS = frozenset({
    'first_packet_ms', 'first_content_ms', 'first_json_closed_ms', 'backend_done_ms',
    'json_closed_to_done_ms', 'thinking_characters', 'content_characters',
    'trailing_whitespace_characters', 'prompt_eval_cached_count',
})


class OutputContractError(ValueError):
    """Fixed codes; no prompt or model output in exception details."""


class OutputTruncated(RuntimeError):
    pass


def dialogue_schema(*, compact=False, omit_action=False):
    if type(omit_action) is not bool or omit_action and not compact:
        raise OutputContractError('invalid_dialogue_schema')
    names = ('a', 'b', 'c') if compact else ('reply_text', 'emotion', 'avatar_action')
    properties = {
        names[0]: {'type': 'string'},
        names[1]: {'type': 'string', 'enum': ['neutral', 'friendly', 'happy', 'sad']},
    }
    if not omit_action:
        properties[names[2]] = {'type': 'string', 'enum': ['']}
    return {'type': 'object', 'properties': properties,
            'required': list(names[:2] if omit_action else names), 'additionalProperties': False}


def build_body(base, payload):
    """Keep all selected text, original sampling/context and generation cap."""
    body = copy.deepcopy(base)
    options = payload['options']
    mode = options.get('output_format', 'json')
    if mode not in FORMATS:
        raise OutputContractError('invalid_output_format')
    if mode != 'json' and (payload['task'] != 'dialogue' or options.get('think', False)):
        raise OutputContractError('incompatible_output_format')
    body.update(messages=copy.deepcopy(payload['messages']), stream=True,
                format=('json' if mode == 'json' else dialogue_schema(compact=mode in ('dialogue_abc_v1', 'dialogue_ab_v1'),
                                                                       omit_action=mode == 'dialogue_ab_v1')),
                keep_alive=-1, think=options.get('think', False))
    body['options']['num_predict'] = options.get('num_predict', 512 if payload['task'] == 'summary' else 120)
    return body


def _unique(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise OutputContractError('duplicate_output_key')
        result[key] = value
    return result


def canonicalize_compact(raw, *, mode='dialogue_abc_v1'):
    """Restore canonical keys only after a whole, bounded object was received."""
    if mode not in ('dialogue_abc_v1', 'dialogue_ab_v1'):
        raise OutputContractError('invalid_compact_mode')
    if not isinstance(raw, str) or not raw:
        raise OutputContractError('invalid_compact_output')
    try:
        if len(raw.encode('utf-8')) > 96 * 1024:
            raise OutputContractError('invalid_compact_output')
        value = json.loads(raw, object_pairs_hook=_unique)
    except (ValueError, TypeError, UnicodeError):
        raise OutputContractError('invalid_compact_output') from None
    expected = {'a', 'b'} if mode == 'dialogue_ab_v1' else set(FIELDS)
    if not isinstance(value, dict) or set(value) != expected:
        raise OutputContractError('invalid_compact_fields')
    text = value['a']
    if (not isinstance(text, str) or not 1 <= len(text.strip()) <= 500
            or any(ord(char) < 32 or 0xD800 <= ord(char) <= 0xDFFF for char in text)
            or '<think' in text.lower()
            or not isinstance(value['b'], str) or value['b'] not in {'neutral', 'friendly', 'happy', 'sad'}
            or mode == 'dialogue_abc_v1' and value['c'] != ''):
        raise OutputContractError('invalid_compact_content')
    canonical = dict(reply_text=text, emotion=value['b'], avatar_action='')
    return json.dumps(canonical, ensure_ascii=False, separators=(',', ':'))


class StreamObservation:
    """O(characters) metadata observation; never releases or stores a fragment.

    First complete braces mean only syntactic closure, never approval to play.
    The host continues until done and the board still validates the full reply.
    """
    def __init__(self, started):
        self.started = started
        self.values = {'thinking_characters': 0, 'content_characters': 0,
                       'trailing_whitespace_characters': 0}
        self.stack, self.in_string, self.escaped = [], False, False
        self.root_started = self.closed = self.invalid = False
        self.pending_whitespace = 0

    def packet(self, packet, now):
        elapsed = max(0., (now - self.started) * 1000)
        self.values.setdefault('first_packet_ms', elapsed)
        message = packet.get('message') or {}
        if not isinstance(message, dict):
            return
        thinking = message.get('thinking')
        if isinstance(thinking, str):
            self.values['thinking_characters'] += len(thinking)
        content = message.get('content') or ''
        if isinstance(content, str) and content:
            self.values.setdefault('first_content_ms', elapsed)
            self.values['content_characters'] += len(content)
            for char in content:
                self.pending_whitespace = self.pending_whitespace + 1 if char.isspace() else 0
                if self.closed:
                    if not char.isspace(): self.invalid = True
                    continue
                if self.in_string:
                    if self.escaped: self.escaped = False
                    elif char == '\\': self.escaped = True
                    elif char == '"': self.in_string = False
                    continue
                if char == '"':
                    self.in_string = True
                elif char in '{[':
                    if not self.root_started:
                        self.root_started = True
                        if char != '{': self.invalid = True
                    self.stack.append('}' if char == '{' else ']')
                elif char in '}]':
                    if not self.stack or self.stack.pop() != char:
                        self.invalid = True
                    elif not self.stack:
                        self.closed = True
                        if not self.invalid:
                            self.values.setdefault('first_json_closed_ms', elapsed)
                elif not self.root_started and not char.isspace():
                    self.invalid = True
        if packet.get('done') is True:
            self.values['backend_done_ms'] = elapsed
            self.values['trailing_whitespace_characters'] = self.pending_whitespace
            closed = self.values.get('first_json_closed_ms')
            if closed is not None and not self.invalid:
                self.values['json_closed_to_done_ms'] = max(0., elapsed - closed)
            elif self.invalid:
                self.values.pop('first_json_closed_ms', None)

    def finish(self, packet):
        if packet.get('done_reason') == 'length':
            raise OutputTruncated('backend_output_truncated')
        cached = packet.get('prompt_eval_cached_count')
        if type(cached) is int and 0 <= cached < 10 ** 15:
            self.values['prompt_eval_cached_count'] = cached
        return {key: value for key, value in self.values.items()
                if type(value) in (int, float) and math.isfinite(value) and 0 <= value < 10 ** 15}
