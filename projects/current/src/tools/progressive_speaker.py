"""Reuse one existing CPU encoder for temporary anonymous voice descriptors."""
import sqlite3
from common.asr_wire import context
from common.speaker_identity import voiced_pcm
from tools.provisional_voice import ProvisionalVoiceMatcher

class ProgressiveSpeakerAnalyzer:
    def __init__(self,device,anonymous_store,*,enabled=False,quality=voiced_pcm):
        if type(enabled) is not bool:raise ValueError('Explicit anonymous collection configuration required')
        if anonymous_store.model_id!=device.encoder.model_id or anonymous_store.dimension!=device.encoder.dimension:
            raise ValueError('Anonymous and named voice models differ')
        self.device=device;self.anonymous_store=anonymous_store;self.enabled=enabled;self.quality=quality
        self.provisional=ProvisionalVoiceMatcher(device,clock=anonymous_store.clock)
    def analyze(self,meta,pcm,*,is_current=lambda:True):
        """Return (legacy descriptive voice evidence, optional anonymous alias)."""
        context(meta,pcm);device=self.device
        if not self.enabled:return device.analyze(meta,pcm),None
        if not is_current():raise InterruptedError('Speaker analysis cancelled')
        revision=self.anonymous_store.revision
        result=dict(state='NOT_CALIBRATED',model_id=device.encoder.model_id,gallery_revision=device.store.revision,
          candidate_id=None,score=None,voiced_ms=0,field_calibrated=device.calibrated,single_speaker_verified=False,consecutive_distinct=0)
        try:
            raw,quality=self.quality(pcm)
            duration=min(20000,round(quality['vad_speech_seconds']*1000))
            vector=device.encoder.encode(raw)
        except (ValueError,KeyError):
            result['state']='INSUFFICIENT_SPEECH'
            return result,self.anonymous_store.unavailable(meta)
        if not self.enabled or not is_current():raise InterruptedError('Anonymous collection stopped')
        result['voiced_ms']=duration
        # Uncalibrated matching remains separate from the legacy calibrated
        # evidence. Any linked name is explicitly provisional and grants nothing.
        try:
            alias=self.anonymous_store.observe(meta,vector,voiced_ms=duration,expected_revision=revision,
              is_current=lambda:self.enabled and is_current())
        except (TimeoutError,sqlite3.Error,ValueError):
            alias=self.anonymous_store.unavailable(meta,'ANONYMOUS_REGISTRY_UNAVAILABLE')
        if not device.calibrated:
            self.provisional.observe(meta,vector,is_current=is_current)
            return result,alias
        if not device.store.people():result['state']='NO_ENROLLMENT';return result,alias
        matched=device.store.match(vector)
        if matched.revision!=result['gallery_revision'] or device.store.revision!=matched.revision:
            result['state']='UNAVAILABLE';return result,alias
        result['state']='CANDIDATE' if matched.state=='KNOWN' else matched.state
        result['score']=matched.score
        if matched.state=='KNOWN':result['candidate_id']=matched.identity_id
        return result,alias
