"""Second phase after board-validated ASR, using the original turn owner."""
from common.asr_wire import context


def text_request(value):
    if not isinstance(value, dict) or set(value) != {'context', 'text', 'reply_text'}:
        raise ValueError('Invalid voice text request')
    meta = context(value['context'])
    text, reply = value['text'], value['reply_text']
    if (not isinstance(text, str) or not 1 <= len(text) <= 4096
            or any(ord(c) < 32 for c in text)):
        raise ValueError('Invalid recognized text')
    if reply is not None and (not isinstance(reply, str) or not 1 <= len(reply) <= 240
                              or any(ord(c) < 32 for c in reply)):
        raise ValueError('Invalid identity feedback text')
    return meta, text, reply
