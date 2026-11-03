"""Temporary demo: independent local mouths for all three speaking emotions."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import sys

from PIL import Image

HERE=Path(__file__).resolve().parent
AURA=HERE.parent.parent/'aura'
sys.path.insert(0,str(AURA))
from board.interaction.avatar_player import AvatarPlayer
from board.interaction.avatar_timing import Segments
from tools.demo_script import ScriptRunner,report,run_window


class ReusePreviewPlayer(AvatarPlayer):
    """Use the normal FSM/render/stop path, with a forward local-mouth loop."""
    CANDIDATE='talking_calm_reuse_v1'
    VARIANT='talking_calm_reuse_v1_b'
    REUSE_POOLS={
        'SPEAKING_NEUTRAL':(CANDIDATE,VARIANT),
        'SPEAKING':('talking_high_reuse_v1','talking_high_reuse_v1_b'),
        'SPEAKING_LOW':('talking_low_reuse_v1',),
    }
    MOUTH_CLOSE_SECONDS=.18
    def __init__(self):
        super().__init__()
        self._reuse_frames={}
        self._reuse_anchors={}
        for name in (self.CANDIDATE,self.VARIANT):
            paths=sorted((HERE/'candidates'/name).glob('*.png'))
            if len(paths)!=39:raise ValueError('Expected the verified 39-frame candidate: '+name)
            images=[]
            for p in paths:
                with Image.open(p) as im:images.append(im.convert('RGBA'))
            # Exported tail frames are recovery material, not a long speech pause.
            active=images[4:31] if name==self.CANDIDATE else images[2:33]
            self._reuse_anchors[name]=images[0]
            self._reuse_frames[name]=self.mouth_cycle(images[0],active)
        self.load_emotional_mouths()
        self._reuse_segments={name:Segments((0,0),(0,len(images)-1),(len(images)-1,len(images)-1))
                              for name,images in self._reuse_frames.items()}

    @staticmethod
    def mouth_cycle(anchor,active):
        # One brief closure at the seam, with adjacent soft opening/closing.
        return [anchor,Image.blend(anchor,active[0],.45),*active,
                Image.blend(active[-1],anchor,.55),anchor]

    def load_emotional_mouths(self):
        profile=json.loads((HERE/'emotion_profile.json').read_text(encoding='utf-8'))
        spec=profile['mouth']
        mask=Image.new('L',(464,480),0)
        pixels=mask.load()
        for y in range(math.floor(spec['cy']-spec['ry']),math.ceil(spec['cy']+spec['ry'])):
            for x in range(math.floor(spec['cx']-spec['rx']),math.ceil(spec['cx']+spec['rx'])):
                radius=math.hypot((x+.5-spec['cx'])/spec['rx'],(y+.5-spec['cy'])/spec['ry'])
                u=max(0.0,min(1.0,(1.0-radius)/(1.0-spec['solid'])))
                pixels[x,y]=round(255*u*u*(3.0-2.0*u))
        for name,data in profile['assets'].items():
            path=AURA/'assets/avatar'/data['anchor']/'000000.png'
            assert hashlib.sha256(path.read_bytes()).hexdigest()==data['anchorSha256']
            with Image.open(path) as image:anchor=image.convert('RGBA')
            active=[]
            for row in data['frames']:
                path=AURA/'assets/avatar'/data['source']/f"{row['frame']:06d}.png"
                assert hashlib.sha256(path.read_bytes()).hexdigest()==row['sha256']
                with Image.open(path) as image:source=image.convert('RGBA')
                m=row['matrix'];a,b,c=m[0];d,e,f=m[1];det=a*e-b*d
                inverse=(e/det,-b/det,(b*f-e*c)/det,-d/det,a/det,(d*c-a*f)/det)
                aligned=source.transform(anchor.size,Image.Transform.AFFINE,inverse,Image.Resampling.BICUBIC)
                composed=Image.composite(aligned,anchor,mask)
                composed.putalpha(anchor.getchannel('A'))
                active.append(composed)
            self._reuse_anchors[name]=anchor
            self._reuse_frames[name]=self.mouth_cycle(anchor,active)

    def pool(self,state):
        return self.REUSE_POOLS[state] if state in self.REUSE_POOLS else super().pool(state)

    def sequence(self,state,asset=None):
        name=asset or self.asset_of(state)
        if state in self.REUSE_POOLS and name in self._reuse_frames:
            return self._reuse_frames[name],24.0,False,name
        return super().sequence(state,asset)

    def sop(self,state,asset=None):
        name=asset or self.asset_of(state)
        if state in self.REUSE_POOLS and name in self._reuse_segments:
            return None,self._reuse_segments[name],1.0
        return super().sop(state,asset)

    def segment_stage_time(self,state,seg,fps,phase,t_stage):
        if state not in self.REUSE_POOLS:
            return super().segment_stage_time(state,seg,fps,phase,t_stage)
        sid=self._time_key if self._time_key is not None else state
        if sid!=self._stage_key:
            self._stage_key=sid
            self.stage_reset()
        if self._stage in ('enter','loop'):
            self._stage='loop'
            length=seg.loop[1]-seg.loop[0]
            self._loop_round=int(t_stage*fps/length)
            position=(max(0.0,t_stage)*fps)%length
            self._source_position=position
            if not self._exit_requested:
                return position/fps,position/fps,0.0
            self._blend_from=position
            self._stage,self._stage_t0='blend',t_stage
        # These frames have pixel-identical body/eyes/alpha. The shared tuple
        # compositor therefore fades only the local mouth, never two gestures.
        elapsed=max(0.0,t_stage-self._stage_t0)
        u=min(1.0,elapsed/self.MOUTH_CLOSE_SECONDS)
        if u>=1.0:
            self._stage='exit'
            self._exit_done=True
            self._source_position=0.0
            return 0.0,0.0,0.0
        self._source_position=self._blend_from
        return self._blend_from/fps,0.0,u*u*(3.0-2.0*u)


def main():
    ap=argparse.ArgumentParser(description='AURA existing-material reuse preview')
    ap.add_argument('--window',action='store_true')
    ap.add_argument('--qt-window',action='store_true')
    args=ap.parse_args()
    core=ReusePreviewPlayer()
    if args.qt_window:
        from preview_window_qt import run_window as run_qt_window
        trace=run_qt_window(core)
        return 1 if trace.errors or trace.rejected else 0
    if args.window:
        return 1 if run_window(core).errors else 0
    runner=ScriptRunner(core,dt=1/30,sample_every=.5)
    trace=runner.run(quiet=True)
    report(trace,core)
    return 1 if trace.errors or trace.rejected else 0


if __name__=='__main__':raise SystemExit(main())
