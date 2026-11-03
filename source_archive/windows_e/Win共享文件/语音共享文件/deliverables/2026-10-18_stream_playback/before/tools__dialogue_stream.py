"""Incremental reply_text decoding with the current 27B prompt and settings."""
import http.client
import json
import socket
import threading
import time
from urllib.parse import urlsplit


class ReplyDecoder:
    """Flat JSON string object; never expose JSON escapes as spoken text."""
    def __init__(self):
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
                if not isinstance(key, str) or key not in {'reply_text', 'emotion', 'avatar_action'} or key in self.values:
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
        parsed = json.loads(self.buffer)
        if (self.state != 'end' or set(self.values) != {'reply_text', 'emotion', 'avatar_action'}
                or parsed != self.values or not self.spoken.strip()
                or self.values['emotion'] not in {'neutral', 'friendly', 'happy', 'sad'}
                or self.values['avatar_action'] != ''):
            raise ValueError('Incomplete or invalid streamed reply')
        return self.values


class OllamaReplyStream:
    def __init__(self, host, model, history, text, timeout):
        self.host, self.model, self.history, self.text = host, model, history, text
        self.timeout = timeout
        self.cancelled = threading.Event()
        self.sock = None

    def cancel(self):
        self.cancelled.set()
        if self.sock:
            try: self.sock.shutdown(socket.SHUT_RDWR)
            except OSError: pass

    def __iter__(self):
        from tools import dialogue_host_ollama as dialogue
        target = urlsplit(self.host)
        if target.scheme != 'http' or target.path not in ('', '/'):
            raise ValueError('Expected local HTTP Ollama host')
        system = dialogue.fast_system_prompt()
        body = dialogue.chat_body(self.model, system, self.text, self.history, fast=True)
        body['stream'] = True  # Same weights, quantization, prompt and sampling settings.
        conn = http.client.HTTPConnection(target.hostname, target.port or 80, timeout=self.timeout)
        decoder = ReplyDecoder()
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
                text = decoder.feed(delta)
                if text: yield 'text', text
                if packet.get('done'):
                    reply = decoder.finish()
                    yield 'complete', reply
                    return
            raise InterruptedError('Reply cancelled or timed out')
        finally:
            timer.cancel()
            conn.close()
            self.sock = None
