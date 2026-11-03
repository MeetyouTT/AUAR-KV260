"""Local model-side device API. Failures do not gate ordinary conversation."""
import base64,http.client,json,re,time

def call(path,value=None,*,timeout=.25):
    c=http.client.HTTPConnection('127.0.0.1',8812,timeout=timeout)
    try:
        c.request('POST' if value is not None else 'GET',path,
                  None if value is None else json.dumps(value).encode(),{'Content-Type':'application/json'})
        r=c.getresponse();raw=r.read(16385)
        if r.status!=200 or len(raw)>16384:raise ValueError('Device service unavailable')
        return json.loads(raw)
    finally:c.close()

def recall(meta,text):
    history=bool(re.search('刚才|之前|之前看到|画面记忆|最近看到',text))
    try:return call('/v1/memory/recall',{'boot':meta['board_boot_id'],'history':history}).get('observations',[])
    except (OSError,ValueError,http.client.HTTPException):return []

def command(meta,text,pcm):
    if re.fullmatch(r'(请)?(清除|删除|忘记)(全部|所有)?(画面|视觉)(记忆|记录)[。！!？? ]*',text):
        try:
            call('/v1/memory/forget',{'boot':meta['board_boot_id']})
            return '已经清除这次开机的画面观察记录。'
        except (OSError,ValueError):return '画面记录服务暂时不可用，这次没有清除成功。'
    # Hub holds enrollment state by the exact boot/session; ordinary speech
    # is a cheap state check and sends no PCM unless a speaker flow needs it.
    intent=bool(re.search('声纹|我的声音|听声音.*谁|声音.*认识|取消登记|确认保存|确认删除',text))
    try:
        state=call('/v1/speaker/state',{'context':meta},timeout=.2)
        if not intent and not state.get('active'):return None
        return call('/v1/speaker/turn',{'context':meta,'text':text,'pcm':base64.b64encode(pcm).decode()},timeout=12).get('reply')
    except (OSError,ValueError,http.client.HTTPException):
        return '声纹服务暂时不可用，普通聊天仍然可以继续。' if intent else None

class DeviceReplyStream:
    def __init__(self,text):self.text=text;self.stopped=False;self.raw_reply=None;self.thinking_characters=0
    def cancel(self):self.stopped=True
    def __iter__(self):
        if self.stopped:raise InterruptedError('Device reply cancelled')
        yield 'text',self.text
        yield 'complete',{'reply_text':self.text,'emotion':'neutral','avatar_action':''}
