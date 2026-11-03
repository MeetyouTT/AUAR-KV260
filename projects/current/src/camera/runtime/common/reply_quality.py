"""Narrow predicates for streamed question-copy protection and diagnostics."""
import re

_QUESTION = re.compile(r'怎么样|怎么|为什么|什么|多少|哪|[吗么呢]|如何|是否')
_EXPLICIT_TRANSFORM = re.compile(r'复述|重复|转写|转录|改写|改成|纠错|校对|原样|跟我说|跟我念|照着.{0,4}[说念读]')
_NEGATED_TRANSFORM = re.compile(r'(?:不要|别|不用|不必|无需)(?:再|给我|替我)?(?:复述|重复|转写|转录|改写|改成|纠错|校对|原样)')
_GREETING = re.compile(r'^(?:你好[呀啊]?|您好|嗨|嘿|喂|早上好|下午好|晚上好|早安|晚安)')


def question_echo_prefixes(user):
    """Candidate complete copies; used only to hold matching streamed prefixes."""
    if _EXPLICIT_TRANSFORM.search(_NEGATED_TRANSFORM.sub('',user)) or not _QUESTION.search(user):
        return ()
    question=re.sub(r'[\W_]+','',user)
    return tuple(value for value in dict.fromkeys((question,_GREETING.sub('',question,count=1))) if len(value)>=8)


def normalized_reply(value):
    return re.sub(r'[\W_]+','',value)


def possible_question_echo(user, reply):
    """Flag a near-complete question copy, with explicit-transform exceptions.

    This signal cannot judge relevance, paraphrases, ambiguity or all Chinese
    intents. Short confirmations and arbitrary substrings are not flagged.
    """
    return normalized_reply(reply) in question_echo_prefixes(user)
