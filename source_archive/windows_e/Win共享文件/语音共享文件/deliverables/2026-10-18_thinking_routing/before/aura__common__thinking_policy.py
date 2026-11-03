"""CPU-only routing. A wait cue is never counted as a substantive answer."""
import re


def route(text):
    text=str(text).strip()
    deliberate=bool(re.search(r'仔细[想思]|认真[想思]|深[入度]思考|推理|证明|逐步|分步骤|多方案|比较|对比|权衡|计算',text))
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
