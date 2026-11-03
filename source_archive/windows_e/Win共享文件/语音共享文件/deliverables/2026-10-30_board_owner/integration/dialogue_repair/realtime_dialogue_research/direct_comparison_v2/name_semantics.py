"""Conservative public self-name check; no IO or transcript storage.

Designed for the fixed public question '你叫什么名字？', not general NLU,
speaker identity, memory authorization, or a production admission gate.
"""
import re
import unicodedata

ALIASES = ('御笠雪妃', '雪妃', 'YUKI MIKASA')
_ALIAS = '(?:' + '|'.join(re.escape(name) for name in ALIASES) + ')'
_PARTICLE = r'(?:哦|呀|啊|呢|啦|哟|吧|就好|就行|就可以|就好了)?'
_END = r'(?=[，。！？、,.!?；;：:\s]|$)'
_ROLE = r'(?:(?:你(?:的)?|这个)?(?:桌面伙伴|语音伙伴|虚拟伙伴|小伙伴|伙伴)[，,\s]*)?'
_SELF = re.compile(r'(?:我的(?:中文)?(?:名字|姓名|称呼)(?:是|叫|为)|我(?:的)?名叫|我叫|我是|你可以(?:叫我|称呼我)|(?:就)?叫我|称呼我|my name is\s+|i am\s+|i\x27m\s+)[：:\s]*'
                   + _ROLE + _ALIAS + _PARTICLE + _END, re.I)
_NAME_CLAIM = re.compile(r'(?:我的(?:中文)?(?:名字|姓名)(?:是|叫|为)|我(?:的)?名叫|我叫)[：:\s]*([^，。！？,.!?；;：:\s]{1,32})', re.I)
_SELECTED_CLAIM = re.compile(_ROLE + _ALIAS + _PARTICLE + r'$', re.I)
_NEGATIVE = re.compile(r'(?:不是|并非|不叫|不名为|叫的不是)[：:\s]*' + _ALIAS + _PARTICLE + _END, re.I)
_BARE = re.compile(r'^' + _ALIAS + _PARTICLE + r'[。！!，,\s]*$', re.I)


def _outside_quotation(text):
    # Keep a quoted NAME token ('我叫“雪妃”。'), but ignore quoted full claims
    # ('她说：“我叫雪妃。”'). Neither is treated as another speaker's grant.
    for left, right in (('“','”'),('‘','’'),('"','"'),("'","'")):
        text = re.sub(re.escape(left) + '(' + _ALIAS + ')' + re.escape(right), r'\1', text, flags=re.I)
    for pattern in (r'“[^”]*”', r'‘[^’]*’', r'"[^"]*"', r"'[^']*'"):
        text = re.sub(pattern, '', text)
    return text


def assess_name(text):
    if not isinstance(text, str) or not text.strip() or len(text) > 500:
        return {'semantic_check':'UNKNOWN','semantic_reason':'INVALID_OR_EMPTY_TEXT'}
    content = _outside_quotation(unicodedata.normalize('NFKC', text).strip())
    selected = bool(_SELF.search(content) or _BARE.fullmatch(content))
    negative = bool(_NEGATIVE.search(content))
    claims = _NAME_CLAIM.findall(content)
    other_claim = any(not _SELECTED_CLAIM.fullmatch(claim) for claim in claims)
    if selected and re.search(r'(?:如果|假如|假设|比如|例如).{0,16}(?:我叫|我是|我的名字)', content):
        return {'semantic_check':'UNKNOWN','semantic_reason':'HYPOTHETICAL_SELF_IDENTIFICATION'}
    if selected and re.search(r'(?:你说|他说|她说|别人说|资料说|听说|有人说|据说).{0,12}(?:我叫|我是|我的名字)', content):
        return {'semantic_check':'UNKNOWN','semantic_reason':'REPORTED_IDENTITY_CLAIM'}
    if selected and (negative or other_claim):
        return {'semantic_check':'UNKNOWN','semantic_reason':'CONFLICTING_IDENTITY_CLAIMS'}
    if negative:
        if '?' in content or '？' in content:
            return {'semantic_check':'UNKNOWN','semantic_reason':'UNCERTAIN_IDENTITY'}
        return {'semantic_check':'FAIL','semantic_reason':'NEGATES_SELECTED_SELF_NAME'}
    if other_claim:
        return {'semantic_check':'FAIL','semantic_reason':'DECLARES_OTHER_SELF_NAME'}
    if selected:
        return {'semantic_check':'PASS','semantic_reason':'SELECTED_SELF_NAME'}
    return {'semantic_check':'UNKNOWN','semantic_reason':'NO_CLEAR_SELF_IDENTIFICATION'}
