"""Existing eye/mouth pixels driven by a live output sample clock."""
from tools.facial_layers import BlinkLayer,MouthBank,interpolate
from board.interaction.avatar_timing import idle_offsets
from tools.idle_body_compositor import IdleBodyTrack,composite_idle_mouth

class RealtimeFacials:
    def __init__(self,core):
        self.core=core;self.eyes=BlinkLayer();self.mouths=MouthBank(core)
        core.audio_mouth_assets=frozenset(self.mouths.keys)
        self.body=IdleBodyTrack(core)
        self.envelope=None;self.closing=None;self.last_gain=0.;self.last_level=0.;self.last_asset=None

    def begin(self,envelope):
        self.envelope=envelope;self.closing=None;self.last_gain=0;self.last_level=0

    def stop(self,now):
        if self.last_gain>0 and self.last_asset:
            self.closing={'at':now,'gain':self.last_gain,'level':self.last_level,'asset':self.last_asset}
        self.envelope=None

    def values(self,audio_time,playing,now):
        if playing and self.envelope:
            return (interpolate(self.envelope['gains'],audio_time,self.envelope['hop_seconds']),
                    interpolate(self.envelope['levels'],audio_time,self.envelope['hop_seconds']))
        if self.closing:
            u=max(0,min(1,(now-self.closing['at'])/.18));gain=self.closing['gain']*(1-u*u*(3-2*u))
            if u>=1:self.closing=None;return 0.,0.
            return gain,self.closing['level']
        return 0.,0.

    def apply(self,meta,now,gain,level):
        result=dict(meta);asset=meta['asset'];result.update(speech_gain=gain,mouth_level=level)
        if asset in self.mouths.keys or meta.get('display_state')=='IDLE':
            # Only this path ends in the existing native fused pose. Mouth
            # compositing, effects-off and ordinary PIL consumers need pixels.
            defer_blend=(asset not in self.mouths.keys and meta.get('display_state')=='IDLE'
                and getattr(self.core,'native_pixels',None) is not None
                and getattr(self.core,'defer_portrait_offsets',False) and self.core.idle_gain>0)
            body,face=(self.body.sample(now,defer_blend=True) if defer_blend else self.body.sample(now))
            result.update(body_asset=body['asset'],body_index=body['index'],
                          body_source_position=body['source_position'],body_face_matrix=face.tolist())
            result['image']=body['image']
        if asset in self.mouths.keys:
            mouth=self.mouths.image(asset,level,1)
            image=composite_idle_mouth(body['image'],mouth,self.body.mouth_matrix(asset,face),gain)
            if self.core.idle_gain>0 and not getattr(self.core, "defer_portrait_offsets", False):image=self.core._apply_offsets(image,idle_offsets(now,gain=self.core.idle_gain))
            result['image']=image;self.last_gain=gain;self.last_level=level;self.last_asset=asset
        else:self.last_gain=0.;self.last_level=0.;self.last_asset=None
        result["portrait_offsets_deferred"]=getattr(self.core, "defer_portrait_offsets", False)
        return self.eyes.apply(result,now,self.core)
