"""Incremental reply_text decoding with the current 27B prompt and settings."""
import http.client
import json
import socket
import threading
import time
from urllib.parse import urlsplit

# Compact internal keys save serialized tokens before speech and metadata.
# Canonical fields are restored by ReplyDecoder before application delivery.
REPLY_FIRST_FIELDS={'a':'reply_text','b':'emotion','c':'avatar_action'}


def stream_body(model, history, text, *, think=False, num_predict=None, reply_first=False):
    from tools import dialogue_host_ollama as dialogue
    system=dialogue.fast_system_prompt()
    if think:
        system=system.replace('通常一两句，最多48个中文字。','先仔细核算与推理，再给出结论及必要解释，最多200个中文字。')
    body=dialogue.chat_body(model,system,text,history,fast=True)
    body.update(stream=True,think=bool(think))
    if num_predict is not None:body['options']['num_predict']=int(num_predict)
    if reply_first:
        # The installed native Ollama path sorts schema property names. Keep
        # all three fields, while making its fixed order begin with speech.
        properties=body['format']['properties']
        body['format']['properties']={key:properties[value] for key,value in REPLY_FIRST_FIELDS.items()}
        body['format']['required']=list(REPLY_FIRST_FIELDS)
        for key,value in REPLY_FIRST_FIELDS.items():
            body['messages'][0]['content']=body['messages'][0]['content'].replace(value,key)
    return body


def wire_history_within_budget(model, history, text):
    """Conservative byte budget; fall back rather than shorten user history.

    This is a guard, not a tokenizer or an assertion of an actual KV-cache hit.
    Reserve room for message framing and the existing generation allowance.
    """
    body=stream_body(model,history,text,reply_first=True)
    content_bytes=sum(len(message['content'].encode('utf-8')) for message in body['messages'])
    allowance=256+32*len(body['messages'])+body['options']['num_predict']
    return content_bytes+allowance<=body['options']['num_ctx']


class ReplyDecoder:
    """Flat JSON string object; never expose JSON escapes as spoken text."""
    def __init__(self, *, field_names=None):
        self.field_names=field_names or {name:name for name in ('reply_text','emotion','avatar_action')}
        self.buffer = ''
        self.pos = 0
        self.state = 'object'
        self.key = None
        self.values = {}
        self.value = ''
        self.spoken = ''

    def feed(self, delta):
        self.buffer += delta
        if len(self.buffer) > 8192:
            raise ValueError('LLM response exceeds bound')
        emitted = ''
        while self.pos < len(self.buffer):
            c = self.buffer[self.pos]
            if self.state != 'string' and c.isspace():
                self.pos += 1
                continue
            if self.state == 'object':
                if c != '{': raise ValueError('Expected JSON object')
                self.state = 'key'
            elif self.state == 'key':
                try:
                    key, end = json.JSONDecoder().raw_decode(self.buffer, self.pos)
                except json.JSONDecodeError:
                    break
                key=self.field_names.get(key) if isinstance(key,str) else None
                if key not in {'reply_text', 'emotion', 'avatar_action'} or key in self.values:
                    raise ValueError('Unexpected or repeated reply key')
                self.key = key
                self.pos = end
                self.state = 'colon'
                continue
            elif self.state == 'colon':
                if c != ':': raise ValueError('Expected JSON colon')
                self.state = 'quote'
            elif self.state == 'quote':
                if c != '"': raise ValueError('Reply values must be strings')
                self.value = ''
                self.state = 'string'
            elif self.state == 'string':
                if c == '"':
                    self.values[self.key] = self.value
                    self.state = 'comma'
                else:
                    step = 1
                    if c == '\\':
                        if self.pos + 1 >= len(self.buffer): break
                        step = 6 if self.buffer[self.pos + 1] == 'u' else 2
                        if self.pos + step > len(self.buffer): break
                        fragment = self.buffer[self.pos:self.pos + step]
                        value = json.loads('"' + fragment + '"')
                        if len(value) == 1 and 0xD800 <= ord(value) <= 0xDBFF:
                            step = 12
                            if self.pos + step > len(self.buffer): break
                            value = json.loads('"' + self.buffer[self.pos:self.pos + step] + '"')
                    else:
                        value = c
                    if any(ord(v) < 32 or 0xD800 <= ord(v) <= 0xDFFF for v in value):
                        raise ValueError('Invalid spoken string character')
                    self.value += value
                    if self.key == 'reply_text':
                        emitted += value
                        self.spoken += value
                        if len(self.spoken) > 240: raise ValueError('Spoken reply exceeds limit')
                    self.pos += step
                    continue
            elif self.state == 'comma':
                if c == ',': self.state = 'key'
                elif c == '}': self.state = 'end'
                else: raise ValueError('Expected JSON comma or end')
            elif self.state == 'end':
                raise ValueError('Data after reply JSON')
            self.pos += 1
        return emitted

    def finish(self):
        parsed=json.loads(self.buffer)
        if not isinstance(parsed,dict):raise ValueError('Expected reply object')
        parsed = {self.field_names.get(key):value for key,value in parsed.items()}
        if (self.state != 'end' or set(self.values) != {'reply_text', 'emotion', 'avatar_action'}
                or parsed != self.values or not self.spoken.strip()
                or self.values['emotion'] not in {'neutral', 'friendly', 'happy', 'sad'}
                or self.values['avatar_action'] != ''):
            raise ValueError('Incomplete or invalid streamed reply')
        return self.values


class OllamaReplyStream:
    def __init__(self, host, model, history, text, timeout, *, think=False, num_predict=None, reply_first=False):
        self.host, self.model, self.history, self.text = host, model, history, text
        self.timeout = timeout
        self.think,self.num_predict=bool(think),num_predict
        self.reply_first=bool(reply_first);self.metrics={}
        self.raw_reply=None
        self.thinking_characters=0
        self.cancelled = threading.Event()
        self.sock = None

    def cancel(self):
        self.cancelled.set()
        if self.sock:
            try: self.sock.shutdown(socket.SHUT_RDWR)
            except OSError: pass

    def __iter__(self):
        target = urlsplit(self.host)
        if target.scheme != 'http' or target.path not in ('', '/'):
            raise ValueError('Expected local HTTP Ollama host')
        body=stream_body(self.model,self.history,self.text,think=self.think,num_predict=self.num_predict,
                         reply_first=self.reply_first)
        conn = http.client.HTTPConnection(target.hostname, target.port or 80, timeout=self.timeout)
        decoder = ReplyDecoder(field_names=REPLY_FIRST_FIELDS if self.reply_first else None)
        started=time.perf_counter();speech_ready=False
        timer = threading.Timer(self.timeout, self.cancel)
        timer.daemon = True
        try:
            conn.connect()
            self.sock = conn.sock
            timer.start()
            if self.cancelled.is_set(): raise InterruptedError('Reply cancelled')
            conn.request('POST', '/api/chat', json.dumps(body).encode(), {'Content-Type': 'application/json'})
            response = conn.getresponse()
            if response.status != 200: raise RuntimeError('Ollama HTTP ' + str(response.status))
            while not self.cancelled.is_set():
                raw = response.readline(32769)
                if not raw: raise EOFError('Ollama ended before completion')
                if len(raw) > 32768: raise ValueError('Ollama packet exceeds limit')
                packet = json.loads(raw)
                if packet.get('error'): raise RuntimeError(str(packet['error'])[:200])
                delta = (packet.get('message') or {}).get('content') or ''
                if delta and 'first_raw_content_ms' not in self.metrics:
                    self.metrics['first_raw_content_ms']=round((time.perf_counter()-started)*1000,2)
                self.thinking_characters+=len((packet.get('message') or {}).get('thinking') or '')
                text = decoder.feed(delta)
                if text and 'first_reply_text_ms' not in self.metrics:
                    self.metrics['first_reply_text_ms']=round((time.perf_counter()-started)*1000,2)
                if text: yield 'text', text
                if not speech_ready and 'reply_text' in decoder.values:
                    speech_ready=True
                    yield 'speech_ready',None
                if packet.get('done'):
                    reply = decoder.finish()
                    self.raw_reply=decoder.buffer
                    self.metrics.update({key:packet[key] for key in ('prompt_eval_count','eval_count','done_reason') if key in packet})
                    for key in ('load_duration','prompt_eval_duration','eval_duration','total_duration'):
                        if isinstance(packet.get(key),(int,float)):self.metrics[key+'_ms']=round(packet[key]/1e6,2)
                    yield 'complete', reply
                    return
            raise InterruptedError('Reply cancelled or timed out')
        finally:
            timer.cancel()
            conn.close()
            self.sock = None
