"""Offline-reviewed candidate for a fully validated board-owned reply.

Pure stdlib; no models, network, files, permissions, threads or device calls.
This is conservative punctuation grouping, not a semantic end-of-turn model.
The caller must still validate the COMPLETE LLM JSON before calling this code.
"""
from __future__ import annotations

import re


class ChunkPolicyError(ValueError):
    """Fixed codes only; never place the reply text into an error."""


_STRONG = frozenset('。！？!?；;')
_SOFT = frozenset('，,、 ')
_PAIRS = {'（': '）', '(': ')', '[': ']', '【': '】', '《': '》',
          '“': '”', '‘': '’', '「': '」', '『': '』', '{': '}'}
_CLOSERS = frozenset(_PAIRS.values()) | {'"'}
_QUOTE_CLOSERS = frozenset('”’」』"')
# Keep URL queries, numeric separators and identifiers inside their tokens.
_URL = re.compile(r'(?:https?://|www\.)[^\s，。！？；“”‘’（）《》<>]+')
_SHORT_ACKS = frozenset({'嗯', '哦', '好', '好的', '是的', '明白', '明白了', '当然',
                         '当然可以', '可以', '没问题', '对', '是', '嗯嗯'})


def _content_count(text):
    return sum(char.isalnum() for char in text)


def _boundaries(text):
    protected = set()
    for match in _URL.finditer(text):
        protected.update(range(match.start(), match.end()))
    strong, soft, stack = [], [], []
    pending = False
    for index, char in enumerate(text):
        if index in protected:
            pending = False
            continue
        if char == '"':
            if stack and stack[-1] == char:
                stack.pop()
            else:
                stack.append(char)
                pending = False
        elif char in _PAIRS:
            stack.append(_PAIRS[char])
            pending = False
        elif stack and char == stack[-1]:
            stack.pop()
            # A sentence inside parentheses can be followed by the main
            # clause. Only a closing quotation mark carries its end marker.
            if char not in _QUOTE_CLOSERS:
                pending = False
        elif char in _STRONG:
            pending = True
        elif char not in _CLOSERS:
            pending = False
        if not stack and char in _SOFT:
            numeric_separator = (char == ',' and index > 0 and index + 1 < len(text)
                                 and text[index - 1].isdigit() and text[index + 1].isdigit())
            if not numeric_separator:
                soft.append(index + 1)
        next_char = text[index + 1:index + 2]
        if pending and not stack and (not next_char or next_char not in _STRONG | _CLOSERS):
            strong.append(index + 1)
            pending = False
    if not strong or strong[-1] != len(text):
        strong.append(len(text))
    return strong, soft


def segment_reply(text, max_chars=220, *, first_min_content=8, tail_target_content=48):
    """Preserve every character; group known short acknowledgements and tails.

    Bounds are code points, as in the existing wire. A short final reply is
    allowed. No comma split is attempted until a natural unit exceeds the
    existing hard bound. Quoted/bracketed material stays intact. An overlong
    unit without a safe external boundary fails closed, as in the baseline.

    The first threshold applies ONLY to the explicit acknowledgement list;
    substantive terse answers are retained. 8/48 are experiment parameters,
    not measured speech-duration predictions.
    This function must not be applied to provisional/partial model text.
    """
    if type(max_chars) is not int or not 1 <= max_chars <= 240:
        raise ChunkPolicyError('invalid_limit')
    if (type(first_min_content) is not int or not 1 <= first_min_content <= 240
            or type(tail_target_content) is not int or not 1 <= tail_target_content <= 240):
        raise ChunkPolicyError('invalid_grouping')
    if (not isinstance(text, str) or not 1 <= len(text) <= 500
            or any(ord(char) < 32 for char in text) or not _content_count(text)):
        raise ChunkPolicyError('invalid_text')
    strong, soft = _boundaries(text)
    units, start = [], 0
    for end in strong:
        while end - start > max_chars:
            cuts = [cut for cut in soft if start < cut <= start + max_chars
                    and cut < end and _content_count(text[start:cut])]
            if not cuts:
                raise ChunkPolicyError('no_safe_boundary')
            cut = cuts[-1]
            units.append(text[start:cut])
            start = cut
        if start < end:
            units.append(text[start:end])
            start = end
    first = units.pop(0)
    while (units and _content_count(first) < min(first_min_content, max_chars)
           and ''.join(char for char in first if char.isalnum()) in _SHORT_ACKS
           and len(first) + len(units[0]) <= max_chars):
        first += units.pop(0)
    chunks = [first]
    tail = ''
    target = min(tail_target_content, max_chars)
    for unit in units:
        if tail and len(tail) + len(unit) > max_chars:
            chunks.append(tail)
            tail = ''
        tail += unit
        if _content_count(tail) >= target:
            chunks.append(tail)
            tail = ''
    if tail:
        chunks.append(tail)
    if (''.join(chunks) != text or any(not chunk or len(chunk) > max_chars
                                     or not _content_count(chunk) for chunk in chunks)):
        raise ChunkPolicyError('invalid_partition')
    return tuple(chunks)
