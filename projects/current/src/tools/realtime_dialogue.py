"""Optional real host connection; offline means no synthesized mock answers."""
from concurrent.futures import ThreadPoolExecutor
import queue
import uuid
from board.runtime.avatar_actions import ALLOWED_AVATAR_ACTIONS,is_allowed,normalize
from board.runtime.audio.selected_voice import normalize_text
from board.runtime.dialogue_client.adapter import DialogueRequest
from board.runtime.dialogue_client.ws_adapter import WebSocketAdapter

class DialogueConnection:
    def __init__(self,config):
        self.enabled=bool(config.get('enabled',False));self.results=queue.Queue()
        self.normalize_reply=normalize_text
        if config.get('preserve_punctuation'):
            from board.runtime.audio.omnivoice_voice import normalize_omnivoice_text
            self.normalize_reply=normalize_omnivoice_text
        self.timeout=float(config.get('timeout_seconds',30));self.pending=0
        self.executor=ThreadPoolExecutor(max_workers=1,thread_name_prefix='aura-dialogue')
        self.adapter=WebSocketAdapter(host=config.get('host','127.0.0.1'),port=int(config.get('port',8765)),
                       path=config.get('path','/dialogue'),timeout_s=self.timeout,max_retries=0)

    def submit(self,text,generation):
        if not self.enabled:raise ValueError('对话模型未连接，请先在另一台电脑配置服务')
        text=normalize_text(text)
        if self.pending>=4:raise ValueError('对话请求较多，请稍后重试')
        request=DialogueRequest(request_id='xilan-'+uuid.uuid4().hex,audio_generation_id=generation,
                    transcript=text,scene_state={},allowed_emotions=['neutral','friendly','happy','excited','sad','low'],
                    allowed_avatar_actions=list(ALLOWED_AVATAR_ACTIONS))
        self.pending+=1;self.executor.submit(self._run,request,generation)

    def _run(self,request,generation):
        try:
            if not self.adapter.is_connected:self.adapter.connect()
            response=self.adapter.send_request(request,timeout_ms=int(self.timeout*1000))
            if response.protocol_version!='1.0' or response.request_id!=request.request_id:raise ValueError('对话响应协议或请求编号不匹配')
            if response.visual_claims:raise ValueError('当前演示台没有视觉输入，不能接受视觉声明')
            text=self.normalize_reply(response.reply_text);emotion=response.emotion or 'neutral';action=normalize(response.avatar_action)
            if emotion not in request.allowed_emotions or action and not is_allowed(action):raise ValueError('对话返回了不支持的表情或动作')
            self.results.put({'generation':generation,'text':text,'emotion':emotion,'action':action})
        except Exception as exc:
            self.adapter.close()
            self.results.put({'generation':generation,'error':str(exc)})

    def poll(self):
        try:result=self.results.get_nowait();self.pending-=1;return result
        except queue.Empty:return None

    def close(self):
        self.executor.shutdown(wait=False,cancel_futures=True);self.adapter.close()
