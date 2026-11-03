"""Admit existing 27B reasoning into the original board dialogue controller.

No calculator, second model, database, device or inference starts here.
"""
from board.runtime.board_dialogue import StaleGeneration
from common.thinking_policy import route


class LocalReasoningDialogue:
    def __call__(self, text, *, job, controller, is_current, cancel_event):
        if not is_current() or cancel_event.is_set():
            raise StaleGeneration('Reasoning admission no longer owns its input')
        if controller.clock() >= job.deadline:
            raise TimeoutError('Original reasoning turn deadline expired')
        controller.store.check_scope(job.scope)
        if route(text)['mode'] != 'reasoning':
            raise ValueError('No explicit reasoning intent')
        # None rejoins the original prepare_text path with raw admitted input,
        # per-packet prepared-turn authority, original TTS and full player ACK.
        return None
