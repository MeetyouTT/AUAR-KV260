"""Optional social cues; no microphone, session, identity or motion authority.

Input keys must come from a fresh camera snapshot. Caller arbitrates the
existing audio player; a returned proposal is never permission to interrupt.
"""

class VisualSocial:
    def __init__(self, *, stable_seconds=.6, silence_seconds=4., cooldown_seconds=30.):
        self.stable_seconds=stable_seconds
        self.silence_seconds=silence_seconds
        self.cooldown_seconds=cooldown_seconds
        self.key=None;self.since=0.;self.last_frame=None
        self.entered=False;self.prompt_at=None;self.cooldown_until=0.

    def observe(self, key, frame_id, now, *, busy=False, speech_active=False, enabled=True):
        if not enabled or key is None:
            self.key=None;self.entered=False;self.prompt_at=None;self.last_frame=None
            return None
        if key!=self.key:
            self.key=key;self.since=now;self.last_frame=frame_id
            self.entered=False;self.prompt_at=None
            return None
        fresh=frame_id!=self.last_frame
        self.last_frame=frame_id
        if busy or speech_active:
            # A person arriving during a conversation is not greeted later.
            self.entered=True;self.prompt_at=None
            return None
        if not fresh:
            return None
        if not self.entered and now-self.since>=self.stable_seconds:
            self.entered=True
            if now<self.cooldown_until:
                return None
            self.cooldown_until=now+self.cooldown_seconds
            self.prompt_at=now+self.silence_seconds
            return {'kind':'arrival','text':'嗯？'}
        if self.prompt_at is not None and now>=self.prompt_at:
            self.prompt_at=None
            return {'kind':'invitation','text':'想和我聊点什么呀？'}
        return None
