"""Confirm a new spoken interruption before cancelling playback.

Uses the configured CPU ASR only; no LLM, conversation writes or audio files.
Text similarity is an echo veto, not proof of a person's identity.
"""
from concurrent.futures import ThreadPoolExecutor
from difflib import SequenceMatcher
import hashlib
import re
import time
import unicodedata
import uuid

from board.runtime.audio.transcription import recognize
from common.handsfree_entry import acceptable_entry


def classify_interruption(text, spoken):
    def normalized(value):
        return re.sub(r'[^\w\u4e00-\u9fff]', '', unicodedata.normalize('NFKC', value).lower())
    candidate, reference = normalized(text), normalized(spoken)
    if not candidate or not reference:
        return 'unclear'
    # ASR spelling errors must not turn a mostly copied sentence into a new turn.
    matched = sum(block.size for block in SequenceMatcher(None, candidate, reference, autojunk=False).get_matching_blocks())
    if candidate in reference or matched / len(candidate) >= .75:
        return 'echo'
    if acceptable_entry(text) or candidate in {'停', '等等', '停止', '别说了'}:
        return 'new_speech'
    return 'unclear'


class InterruptionVerifier:
    def __init__(self, config_provider, boot_id, *, transport=recognize, clock=time.monotonic):
        self.config_provider, self.boot_id = config_provider, boot_id
        self.transport, self.clock = transport, clock
        self.executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix='aura-barge-confirm')
        self.future = None
        self.closed = False

    def submit(self, pcm, spoken):
        if self.closed or self.future is not None or len(pcm) < 6400:
            return False
        config = dict(self.config_provider())
        meta = {'protocol': 'aura-asr-1', 'board_boot_id': self.boot_id,
                'session_id': uuid.uuid4().hex, 'request_id': uuid.uuid4().hex,
                'capture_id': uuid.uuid4().hex, 'generation': 1,
                'sample_count': len(pcm)//2, 'pcm_sha256': hashlib.sha256(pcm).hexdigest(),
                'budget_ms': 1500}
        def verify():
            started = self.clock()
            try:
                result = self.transport(config, meta, pcm, 1.5)
                text = result['text']
                return {'decision': classify_interruption(text, spoken),
                        'characters': len(text), 'elapsed_ms': round((self.clock()-started)*1000)}
            except Exception as exc:
                return {'decision': 'unavailable', 'error_type': type(exc).__name__}
        self.future = self.executor.submit(verify)
        return True

    def poll(self):
        if self.closed or self.future is None or not self.future.done():
            return None
        future, self.future = self.future, None
        return future.result()

    def close(self):
        self.closed = True
        if self.future:
            self.future.cancel()
        self.executor.shutdown(wait=False)
