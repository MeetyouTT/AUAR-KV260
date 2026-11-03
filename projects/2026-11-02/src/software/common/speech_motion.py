"""Bounded gestures from the spoken clause, scheduled on the PCM timeline.

This policy does not rewrite speech or require another model call. Explicit
model actions take precedence; a conservative prefix policy supplies actions
for the existing latency-oriented model schema which emits an empty action.
"""
import re

ACTION_STATES = {
    'ack_nod': 'ACK_NOD', 'deny_shake': 'DENY_SHAKE',
    'emo_surprised': 'AWAKE', 'emo_puzzled': 'PUZZLED',
}
EMOTIONS = frozenset(('neutral', 'friendly', 'happy', 'sad'))


def clause_motion(text):
    """Classify the speaker's own opening reaction, not quoted/user content."""
    text = str(text).lstrip(' ，。！？、\t\n')
    # A quotation or hypothetical must not look like the speaker's stance.
    if text.startswith(('“', '「', '《', '如果', '假如', '比如', '例如')):
        return 'neutral', ''
    text = re.sub(r'^(?:嗯[，、 ]*|啊[，、 ]*)', '', text)
    rules = (
        (('抱歉', '对不起', '不可以', '不能', '不行', '不是的', '不对', '没办法', '我无法'), 'sad', 'deny_shake'),
        (('我没听清', '没听清', '我没明白', '没明白', '不太明白', '我不确定', '不确定', '你是说', '你的意思是'), 'neutral', 'emo_puzzled'),
        (('哇', '太棒了', '真厉害', '太好了', '没想到', '居然', '真没想到'), 'happy', 'emo_surprised'),
        (('好的', '好呀', '好啊', '可以的', '可以呀', '当然可以', '没问题', '明白了', '知道了', '记住了', '记下了', '对的', '是的', '谢谢'), 'friendly', 'ack_nod'),
    )
    for prefixes, emotion, action in rules:
        if text.startswith(prefixes):
            return emotion, action
    if text.startswith(('很遗憾', '听起来很难过', '别难过')):
        return 'sad', ''
    return 'neutral', ''


class SpeechMotionPlan:
    """At most two distinct gestures per turn, separated by four audio seconds."""
    def __init__(self):
        self.used = set()
        self.last_sample = -96000

    def cue(self, text, at_sample, *, emotion=None, action=''):
        inferred_emotion, inferred_action = clause_motion(text)
        emotion = emotion if emotion in EMOTIONS else inferred_emotion
        action = action if action in ACTION_STATES else inferred_action
        if (not action or action in self.used or len(self.used) >= 2
                or at_sample - self.last_sample < 96000):
            action = ''
        if action:
            self.used.add(action)
            self.last_sample = at_sample
        return dict(emotion=emotion, action=action, at_sample=int(at_sample))
