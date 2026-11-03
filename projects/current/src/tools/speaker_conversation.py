"""ModelHost integration: descriptive attribution never chooses a profile."""
from contextlib import nullcontext
from common.asr_wire import context
from tools.speaker_turn_host import SpeakerTurnRecorder

class SpeakerConversation(SpeakerTurnRecorder):
    def __init__(self,store,*,scope_for=None,**kwargs):
        self.scope_for=scope_for or (lambda meta:nullcontext(None))
        super().__init__(store,**kwargs)
    def begin(self,meta,cid,pcm,visual=None,*,deadline=None):
        owner=context(meta,pcm)
        return self.submit(owner,pcm,cid,visual,scope=lambda:self.scope_for(owner),deadline=deadline)
