"""Existing eye/mouth pixels driven by a live output sample clock."""
from tools.facial_layers import BlinkLayer,MouthBank,interpolate
from board.interaction.avatar_timing import idle_offsets

class RealtimeFacials:
    def __init__(self,core):
        self.core=core;self.eyes=BlinkLayer();self.mouths=MouthBank(core)
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
        if asset in self.mouths.keys:
            image=self.mouths.image(asset,level,gain)
            if self.core.idle_gain>0:image=self.core._apply_offsets(image,idle_offsets(now,gain=self.core.idle_gain))
            result['image']=image;self.last_gain=gain;self.last_level=level;self.last_asset=asset
        else:self.last_gain=0.;self.last_level=0.;self.last_asset=None
        return self.eyes.apply(result,now,self.core)
