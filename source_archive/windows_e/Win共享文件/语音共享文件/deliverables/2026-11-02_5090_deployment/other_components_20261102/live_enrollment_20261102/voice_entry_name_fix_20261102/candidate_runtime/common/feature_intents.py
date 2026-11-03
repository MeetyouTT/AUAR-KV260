"""Narrow speech-only routing; a match conveys no consent beyond original FSMs.

Quoted, hypothetical and negative requests never become enrollment commands.
The raw transcript and captured PCM stay unchanged in their original owner.
"""
import re

from common.character_profile import strip_character_address
from common.spoken_input import prepare_spoken_input


def _speaker_enrollment_value(text):
    """Only enrollment/name intent: preserve questions and reject quoted speech."""
    if not isinstance(text, str) or not 1 <= len(text) <= 2000:
        return None
    if any(ord(char) < 32 for char in text) or re.search(r'[？?"\'“”‘’「」『』]', text):
        return None
    value = strip_character_address(prepare_spoken_input(text)['text'].strip())
    return value.strip(' ，,。！!')


def speaker_enrollment_name(text):
    """Exact self-name slot; callers still need an already explicit voice entry.

    Only whitespace between Chinese name characters is formatting. Punctuation,
    spelling, Latin word boundaries and arbitrary sentence tails are not guessed.
    The original name validator and SpeakerDevice's original 20-char slot apply.
    """
    from common.voice_enrollment import valid_name
    value = _speaker_enrollment_value(text)
    if value is None:return None
    match = re.fullmatch(r'(?:我叫|我的名字是|名字是|叫我)[ 　]*[：:]?[ 　]*(.+)', value)
    if match is None:return None
    name = match[1].strip()
    if re.fullmatch(r'[\u4e00-\u9fff 　]+', name):
        name = re.sub(r'[ 　]+', '', name)
    if (not 1 <= len(name) <= 20 or re.search(r'\s', name)
            or re.search(r'[吗呢么嘛]$|是不是|能不能|可不可以|要不要|好不好', name)
            or re.match(r'(?:不是|不叫|不要|不想|不需要)', name)
            or not valid_name(name)):
        return None
    return name


def _speaker_enrollment_start(text):
    value = _speaker_enrollment_value(text)
    if value is None:return None
    # Whole self-directed commands only, not keyword extraction or prefix erase.
    prefix = r'(?:(?:我要|我想))?(?:请)?(?:帮我|给我)?'
    action = r'(?:(?:登记|注册|录入)(?:一下)?(?:我的)?声纹|登记(?:一下)?(?:我的)?声音)'
    slot = r'(?:我叫|我的名字是|名字是).+'
    match = re.fullmatch(prefix + action + r'(?:[，,。 ：:]*(' + slot + r'))?', value)
    if match is None:
        # Preserve the original explicit, named legacy wording; a bare request
        # here has never been a standalone start and remains unchanged.
        match = re.fullmatch(r'(?:请)?(?:帮我)?记住我的声音[，, ]*(' + slot + r')', value)
    if match is None:return None
    if match[1] is None:return {'name': None}
    name = speaker_enrollment_name(match[1])
    return {'name': name} if name is not None else None


def speaker_text(text, *, active=False):
    """Return the existing speaker FSM's canonical input, or None.

    Arbitrary utterances during an active enrollment are still handled by the
    original sampler. General cancel/save words are only interpreted there.
    """
    if not isinstance(text, str) or not 1 <= len(text) <= 2000:
        return None
    value = strip_character_address(prepare_spoken_input(text)['text'].strip(' \t\r\n。！!？?'))
    value = value.strip(' \t\r\n，,。！!？?')
    if value in ('取消声纹登记', '停止声纹登记', '不登记声纹了', '不要保存声纹'):
        return '取消声纹登记'
    if value in ('确认保存声纹', '确认删除声纹'):
        return value
    if active and value in ('取消登记', '取消', '不保存'):
        return value
    name = r'([^，,。！？!?\s]{1,20})'
    enrollment = _speaker_enrollment_start(text)
    if enrollment is not None:
        return ('登记我的声纹' if enrollment['name'] is None else
                '登记我的声纹，我叫' + enrollment['name'])
    found = re.fullmatch(r'(?:请)?删除声纹[，, ]*(?:名字是|名为)?'+name, value)
    if found:
        return '删除声纹，名字是'+found[1]
    # Read-only questions use the existing readiness/calibration/match path.
    # Full matches prevent quotations and negation from executing an action.
    question = value
    if question.startswith('请问'):
        question = question[2:]
    question = question.removesuffix('？').removesuffix('?')
    if re.fullmatch(r'(?:你)?(?:现在|刚才)?(?:已经)?(?:帮我|给我|为我)?(?:把)?(?:我的)?声纹'
                    r'(?:登记)?(?:保存|录入|登记)(?:成功|完成|好)?(?:了)?[吗呢]?', question):
        return '查询声纹保存状态'
    if re.fullmatch(r'(?:你)?(?:现在|刚才)?(?:有没有|是否|是不是)?(?:已经|还没|还没有)?'
                    r'(?:帮我|给我|为我)?(?:保存|录入|登记)(?:成功|完成|好)?(?:了|过)?'
                    r'(?:我的|本轮的|这次的)?(?:声纹|声音)(?:成功|完成)?(?:了)?[吗呢]?', question):
        return '查询声纹保存状态'
    endings = r'[吗呢么啊呀]?'
    patterns = (
        r'(?:现在)?(?:我的)?声纹(?:识别)?(?:现在)?(?:是否|能否)?(?:可用|能用|正常|就绪|有记录|已登记|登记过)'+endings,
        r'(?:我|我的声音|我的声纹)(?:以前|之前)?(?:已经|曾经)?登记过声纹'+endings,
        r'(?:我)?(?:已经)?登记(?:过|了)声纹'+endings,
        r'(?:请)?(?:查询|检查|识别|辨认)(?:一下)?(?:我的)?(?:声纹|声音)'+endings,
        r'(?:你)?(?:现在)?(?:能|可以|会)?(?:识别|辨认|认出|认识)(?:我的)?(?:声纹|声音)'+endings,
        r'(?:你)?(?:听|听听|根据|通过)(?:我的)?声音(?:你)?(?:能|可以)?(?:知道|判断|识别|认出)?(?:我是谁|谁在说话)'+endings,
        r'(?:你)?(?:能|可以)?(?:根据|通过)(?:我的)?声音(?:识别|认出|辨认)(?:我|我是谁)'+endings,
        r'(?:我的)?声纹(?:是否|有没有|有无)(?:登记|记录|保存)'+endings,
        r'(?:现在)?(?:你的)?声纹(?:识别)?(?:功能)?(?:怎么样|状态如何|准备好了吗|能用了吗)',
    )
    if question == '查询我的声纹' or any(re.fullmatch(p, question) for p in patterns):
        return '查询我的声纹'
    return None


def speaker_requested(text):
    return speaker_text(text) is not None


def speaker_query_requested(text):
    return speaker_text(text) in ('查询我的声纹','查询声纹保存状态')
