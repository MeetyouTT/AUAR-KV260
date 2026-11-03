"""CPU-only routing. A wait cue is never counted as a substantive answer."""
import re

_CLAUSE_BOUNDARY = r'[，,。！？!?；;\n]'
_NEGATED_REQUEST = re.compile(
    r'(?:不用|不必|无需|不要|别|不想)(?:再|去|来|帮我|给我|你|仔细|认真|深入|深度|进行|做|做个|这么|那么|盲目|相互|互相|过多|反复|一下|地)*$'
)
_CASUAL_COMPARISON = re.compile(
    r'^(?:喜欢|开心|快乐|难过|伤心|紧张|焦虑|疲惫|困|累|舒服|轻松|无聊|担心|害怕|在意|愿意|满意|失望|想你|想他|想她|鲜明|强烈)'
)
_STATE_ONLY = re.compile(r'^(?:好|坏|忙|冷|热|多|少|高|低|大|小|远|近|早|晚|快|慢|安静|清楚|便宜|贵)(?:一点|一些|了|吧|呀|啊|呢|啦|的)*$')
_ADJECTIVAL_COMPARISON = re.compile(r'^(?:好|便宜|贵|合适|适合|重要|明显|严重|安静|清楚)(?:的|一点|一些|了|吧|呀|啊|呢|啦|$)')
_COMPARISON_REQUEST = re.compile(r'(?:请|请你|麻烦|麻烦你|帮我|帮忙|替我|给我|能否|能不能|可以|我想|想让你|需要你|我们来|来|进行|做个|做一下|认真|仔细|详细)$')
_COMPARISON_TARGET = re.compile(r'这|那|两个|两种|几个|不同|各个|和|与|还是|\bvs\b|区别|差异|优缺点|利弊|哪个|哪种|方案|模型|配置|方法|版本|路线|产品', re.I)
_DELIBERATE = re.compile(
    r'仔细[想思](?!你|他|她|念)|认真[想思](?!你|他|她|念)|深[入度]思考|'
    r'推理(?!小说|故事|电影|剧|游戏)|证明|逐步(?=分析|解释|推导|计算|说明|讲解|$)|'
    r'分步骤|多方案|权衡|计算(?!机|器)'
)


def _negated(text, offset):
    prefix = re.split(_CLAUSE_BOUNDARY, text[:offset])[-1].strip()
    return bool(_NEGATED_REQUEST.search(prefix))


def _requests_comparison(text):
    for match in re.finditer(r'比较|对比', text):
        prefix = re.split(_CLAUSE_BOUNDARY, text[:match.start()])[-1].strip()
        tail = re.split(_CLAUSE_BOUNDARY, text[match.end():], maxsplit=1)[0].strip()
        if _negated(text, match.start()) or tail.startswith(('了', '过', '完')):
            continue
        if _CASUAL_COMPARISON.match(tail) or _STATE_ONLY.fullmatch(tail):
            continue
        requested = bool(_COMPARISON_REQUEST.search(prefix))
        if _ADJECTIVAL_COMPARISON.match(tail) and not requested:
            continue
        if requested or _COMPARISON_TARGET.search(tail):
            return True
    return False


def route(text):
    text=str(text).strip()
    deliberate=any(not _negated(text,m.start()) for m in _DELIBERATE.finditer(text))
    deliberate=deliberate or _requests_comparison(text)
    arithmetic=len(re.findall(r'\d+(?:\.\d+)?',text))>=2 and bool(re.search(r'加|减|乘|除|折|运费|合计|总共|实付|[+*/×÷]',text))
    complex_request=deliberate or arithmetic or (len(text)>=65 and bool(re.search(r'方案|计划|设计|原因|分析',text)))
    if complex_request:return {'mode':'reasoning','reason':'complex','feedback_after_ms':0}
    # A casual turn should not announce deliberation merely because synthesis
    # is taking time. Reserve the cached thinking phrase for actual reasoning.
    return {'mode':'chat','reason':'delayed','feedback_after_ms':None}


class FeedbackGate:
    def __init__(self,plan):
        self.plan=plan;self.sent=False;self.answer_ready=False;self.cancelled=False

    def due(self,elapsed_ms):
        if self.sent or self.answer_ready or self.cancelled:return False
        if self.plan['feedback_after_ms'] is None:return False
        if elapsed_ms<self.plan['feedback_after_ms']:return False
        self.sent=True
        return True

    def ready(self):self.answer_ready=True
    def cancel(self):self.cancelled=True
