"""Emit synthetic request/output/receipt traces; performs no model or device IO."""
import argparse
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import sys

parser = argparse.ArgumentParser()
parser.add_argument('--runtime', type=Path, required=True)
args = parser.parse_args()
sys.path.insert(0, str(args.runtime.resolve()))
from tests.framework import test_numeric_llm_metrics as f
from tests.framework import test_board_dialogue as original
from board.runtime.board_dialogue import BoardReply

def digest(value):
    raw = json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',', ':')).encode('utf-8')
    return hashlib.sha256(raw).hexdigest()

def trace(name):
    controller, store, models = f.setup()
    backend = dict(first_content_ms=10., backend_done_ms=35., eval_count=8)
    replies = ['我会陪你聊聊。也可以先休息。']
    batches = [backend]
    if name == 'echo_retry':
        replies = [f.USER_TEXT, '我在这里陪你，慢慢说就好。']
        batches = [backend, dict(first_content_ms=11., backend_done_ms=36., eval_count=9)]
    calls = f.response_hook(models, batches, replies=replies)
    original_hook = models.hook
    if name == 'transport_failure':
        def hook(kind, payload, kwargs):
            if kind == 'llm':
                raise TimeoutError()
            return original_hook(kind, payload, kwargs)
        models.hook = hook
    elif name == 'cancel_during_llm':
        def hook(kind, payload, kwargs):
            result = original_hook(kind, payload, kwargs)
            if kind == 'llm':
                controller.cancel('synthetic-session', generation=1)
            return result
        models.hook = hook
    plan = None
    error = None
    ack = None
    try:
        if name == 'scope_denied':
            plan = controller.prepare_text(f.USER_TEXT, scope={'kind': 'profile', 'id': 'synthetic-profile'},
                session_id='synthetic-session', generation=1, budget_ms=3000)
        elif name == 'local_reply':
            plan = controller.prepare_local_reply('合成查询', lambda: BoardReply('本地合成回答。'),
                scope={'kind': 'conversation', 'id': 'synthetic-session'},
                session_id='synthetic-session', generation=1, budget_ms=3000)
        else:
            plan = f.prepared(controller)
        if name == 'incomplete_ack':
            ack = original.ack(controller, plan, complete=False)
        elif name == 'foreign_ack':
            ack = original.ack(controller, plan, playback_token='synthetic-foreign')
        else:
            ack = original.ack(controller, plan)
    except Exception as caught:
        error = type(caught).__name__
    return {
        'requests': [{'kind': kind, 'payload_sha256': digest(payload), 'deadline': kwargs['deadline']}
                     for kind, payload, kwargs in models.calls],
        'cancelled_owners_sha256': digest([owner.as_dict() for owner in models.cancelled]),
        'plan': None if plan is None else {'turn_id': plan.turn_id, 'token': plan.playback_token,
            'reply_sha256': digest(asdict(plan.reply)), 'pcm_sha256': plan.sha256,
            'sample_count': plan.samples, 'sample_rate': plan.sample_rate,
            'chunks': [{'text_sha256': digest(chunk.text), 'owner': chunk.owner.as_dict(),
                        'sample_count': len(chunk.pcm)//2} for chunk in plan.chunks]},
        'store_events': store.events, 'store_rows_sha256': digest(store.rows),
        'ack': ack, 'error': error, 'controller_idle': controller.idle,
    }

scenarios = ('ordinary_two_tts', 'echo_retry', 'incomplete_ack', 'foreign_ack',
             'scope_denied', 'transport_failure', 'cancel_during_llm', 'local_reply')
print(json.dumps({name: trace(name) for name in scenarios}, sort_keys=True))
