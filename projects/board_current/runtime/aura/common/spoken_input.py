"""Conservative interpretation of recognized speech; never rewrites raw ASR."""
import re

from board.runtime.character import CHARACTER_NAME, ASR_ALIASES

SPEECH_INPUT_HINT = (
    '语音转写可能有同音错字，结合上下文理解，不纠正发音或反复纠名。'
    '分清自己与别人的姓名，提到别人姓名不改变自己的身份。'
    '姓名、数字、否定含义不擅改；关键信息拿不准时简短确认。'
)

# These are character-address aliases, not global Chinese spelling corrections.
ALIASES = ASR_ALIASES
_ALIASES = '|'.join(map(re.escape, ALIASES)) if ALIASES else r'(?!)'
_PUNCT = r'[\s，,。！？!?、：:]'
_FOLLOW = r'(?:你|我|今天|现在|最近|早上|晚上|陪|帮|请|能|可以|在吗|记住|记得|啊|呀)'
_VOCATIVE = re.compile(
    r'^\s*(?:(?P<greeting>你好[呀啊]?|嗨|嘿|喂|早上好|下午好|晚上好|早安|晚安)'
    + _PUNCT + r'*)?(?P<alias>' + _ALIASES + r')(?=$|' + _PUNCT + r'|' + _FOLLOW + r')'
)
_DIRECT_TAIL = re.compile(r'^(?:$|' + _PUNCT + r'|你|陪我|帮我|请你|能不能|可以|在吗|[啊呀](?:$|' + _PUNCT + r'))')
_LITERAL = re.compile(
    r'听错|识别错|说的是|指的是|写作|写成|怎么写|怎么读|拼写|原文|原话|别改|不要改|'
    r'名字是|姓名是|我叫|叫我|朋友叫|同学叫|纠正|更正|'
    r'(?:不是|而非).{0,4}(?:' + _ALIASES + '|' + re.escape(CHARACTER_NAME) + r')'
)


def prepare_spoken_input(text):
    """Resolve one known vocative only; retain all other words and negations.

    No acoustic confidence is available here. Unknown words, other people's
    names, numbers and spelling discussions therefore stay exactly as received.
    """
    if not isinstance(text, str):
        raise ValueError('Recognized speech must be text')
    result = {'raw_text': text, 'text': text, 'adjustments': []}
    if _LITERAL.search(text):
        return result
    match = _VOCATIVE.match(text)
    if match:
        start, end = match.span('alias')
        if not match.group('greeting') and not _DIRECT_TAIL.match(text[end:]):
            return result
        result['text'] = text[:start] + CHARACTER_NAME + text[end:]
        result['adjustments'] = [{'start': start, 'end': end, 'from': text[start:end],
                                  'to': CHARACTER_NAME, 'reason': 'character_vocative_homophone'}]
    return result
