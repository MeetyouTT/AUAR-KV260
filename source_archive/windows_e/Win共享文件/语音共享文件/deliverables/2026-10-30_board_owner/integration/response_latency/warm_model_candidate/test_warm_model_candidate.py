"""Actual request methods, fake sockets only; no model/service/network starts."""
import ast
import hashlib
import json
import math
from pathlib import Path
import sys
import threading
import time
from types import SimpleNamespace as NS
from urllib.parse import urlsplit
import unittest

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parents[4]
sys.path.insert(0, str(PROJECT/'aura'))
BEFORE = PROJECT/'aura/tools/model_inference_host.py'
AFTER = HERE/'after/aura/tools/model_inference_host.py'
MODEL = 'aura-qwen3.8-27b-abliterated:iq4_xs'
BEFORE_SHA = 'ace827aa21d9b6c404366677d05fc20054fe88f265af8ca0a20107e082cbf5c8'


class Socket:
    def __init__(self): self.outgoing = b''; self.blocking = True
    def setblocking(self, value): self.blocking = value
    def send(self, raw): self.outgoing += bytes(raw); return len(raw)


class Connection:
    latest = None
    def __init__(self, host, port, timeout):
        self.host, self.port, self.timeout = host, port, timeout
        self.sock = Socket(); self.connected = self.closed = False
        Connection.latest = self
    def connect(self): self.connected = True
    def close(self): self.closed = True


class Response:
    status = 200
    def __init__(self, sock): pass
    def begin(self): pass
    def read(self, limit): return json.dumps(dict(model=MODEL, done=True, response='')).encode()
    def readline(self, limit):
        return json.dumps(dict(done=True, message=dict(content='public-fixture'),
            prompt_eval_count=232, eval_count=35, load_duration=1000000,
            prompt_eval_duration=2000000, eval_duration=3000000, total_duration=6000000)).encode()+b'\n'
    def close(self): pass


def methods(path):
    tree = ast.parse(path.read_text(encoding='utf-8'))
    cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == 'LocalModelBackend')
    return {n.name: n for n in cls.body if isinstance(n, ast.FunctionDef)}


def actual_method(name):
    node = methods(AFTER)[name]
    namespace = dict(json=json, math=math, time=time, urlsplit=urlsplit, MAX_OUTPUT_BYTES=65536,
        http=NS(client=NS(HTTPConnection=Connection, HTTPResponse=Response, HTTPException=OSError)),
        select=NS(select=lambda incoming, outgoing, errors, timeout: ([], outgoing, [])),
        _ResponseSocket=lambda sock, deadline, cancelled: sock)
    exec(compile(ast.fix_missing_locations(ast.Module(body=[node], type_ignores=[])), '<candidate-method>', 'exec'), namespace)
    return namespace[name]


def backend():
    checks = []
    return NS(model=MODEL, ollama_host='http://127.0.0.1:11435',
              _check=lambda deadline, cancelled: checks.append((deadline, cancelled)), checks=checks)


def request_body():
    return json.loads(Connection.latest.sock.outgoing.split(b'\r\n\r\n', 1)[1])


class WarmModelTests(unittest.TestCase):
    def test_exactly_two_request_construction_changes(self):
        raw = BEFORE.read_bytes()
        self.assertEqual(hashlib.sha256(raw).hexdigest(), BEFORE_SHA)
        text = raw.decode('utf-8').replace(
            "keep_alive='30m',\n                    think=False, options={'num_ctx': 2048})",
            "keep_alive=-1,\n                    think=False, options={'num_ctx': 2048})", 1).replace(
            "body.update(messages=payload['messages'], stream=True, format='json',\n",
            "body.update(messages=payload['messages'], stream=True, format='json', keep_alive=-1,\n", 1)
        self.assertEqual(AFTER.read_text(encoding='utf-8'), text)
        ast.parse(text, feature_version=(3, 9))

    def test_preload_request_keeps_same_model_context_and_budget(self):
        value = backend(); cancelled = threading.Event(); deadline = time.monotonic()+5.
        actual_method('_preload_llm_request')(value, deadline=deadline, cancelled=cancelled)
        body = request_body()
        self.assertEqual(body, dict(model=MODEL, prompt='', stream=False, keep_alive=-1,
                                   think=False, options=dict(num_ctx=2048)))
        self.assertEqual((Connection.latest.host, Connection.latest.port), ('127.0.0.1', 11435))
        self.assertTrue(Connection.latest.closed)
        self.assertTrue(all(row == (deadline, cancelled) for row in value.checks))

    def test_dialogue_and_summary_override_legacy_30m_without_sampling_changes(self):
        for task, options, prediction in (('dialogue', {}, 120), ('summary', {}, 512),
                                          ('dialogue', {'num_predict': 77}, 77)):
            with self.subTest(task=task, explicit=options):
                value = backend(); cancelled = threading.Event(); deadline = time.monotonic()+5.
                messages = [dict(role='system', content='public-fixture-system'), dict(role='user', content='public-fixture-input')]
                result = actual_method('_ollama')(value, dict(task=task, messages=messages, options=options),
                                                  deadline=deadline, cancelled=cancelled)
                body = request_body()
                self.assertEqual(body['model'], MODEL)
                self.assertEqual(body['keep_alive'], -1)
                self.assertEqual(body['messages'], messages)
                self.assertEqual(body['think'], False)
                self.assertEqual(body['options'], dict(temperature=.6, num_ctx=2048, num_predict=prediction))
                self.assertEqual(body['format'], 'json')
                self.assertTrue(body['stream'])
                self.assertEqual(result['metrics'], dict(prompt_eval_count=232, eval_count=35,
                    load_duration_ms=1., prompt_eval_duration_ms=2., eval_duration_ms=3., total_duration_ms=6.))
                self.assertTrue(all(row == (deadline, cancelled) for row in value.checks))

    def test_llm_request_still_uses_original_gpu_admission(self):
        entered = []
        class Lease:
            def __enter__(self): entered.append('enter')
            def __exit__(self, *args): entered.append('exit')
        calls = []
        value = backend()
        value.gpu = NS(acquire=lambda kind, **options: (calls.append((kind, options)) or Lease()))
        value._ollama = lambda *args, **kwargs: {'text': 'public-fixture'}
        cancelled = threading.Event(); deadline = time.monotonic()+5.
        result = actual_method('llm')(value, {}, deadline=deadline, cancelled=cancelled)
        self.assertEqual(result['text'], 'public-fixture')
        self.assertEqual(calls, [('llm', dict(deadline=deadline, cancelled=cancelled))])
        self.assertEqual(entered, ['enter', 'exit'])

    def test_tts_ownership_preload_order_and_every_other_method_are_unchanged(self):
        before, after = methods(BEFORE), methods(AFTER)
        changed = [name for name in before if ast.dump(before[name]) != ast.dump(after[name])]
        self.assertEqual(changed, ['_preload_llm_request', '_ollama'])


if __name__ == '__main__': unittest.main()
