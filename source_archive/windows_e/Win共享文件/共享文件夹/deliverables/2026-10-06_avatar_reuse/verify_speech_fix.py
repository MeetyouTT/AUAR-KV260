"""Verify visible mouth openings, fixed regions and real script coverage in all emotions."""
import json
from pathlib import Path
import numpy as np
from PIL import Image

from preview_script import AURA,HERE,ReusePreviewPlayer,ScriptRunner


def mouth_pixels(image):
    # Small mouth-cavity colour proxy, calibrated against the reviewed face sheets.
    # It is not a phoneme detector or a naturalness score.
    # Stop above the red-tinted neck; including it falsely marks a closed mouth open.
    a=np.asarray(image.crop((207,138,244,157)).convert('RGB')).astype(np.int16)
    r,g,b=a[:,:,0],a[:,:,1],a[:,:,2]
    return int(((r>80)&(r>1.25*g)&(r>1.1*b)&(g<185)).sum())


def closed_runs(rows):
    longest={};run=0.0;previous=None
    for row in rows:
        state=row['state']
        contiguous=previous is not None and previous['state']==state and row['t']-previous['t']<.07
        if row['mouth_pixels']<5:run=run+row['t']-previous['t'] if contiguous else 1/30
        else:run=0.0
        longest[state]=max(longest.get(state,0.0),run)
        previous=row
    return longest


def before_measurement():
    records=json.loads((HERE/'speech_review/before_speech_fix_positions.json').read_text(encoding='utf-8'))
    cached={};rows=[]
    for row in records:
        state=row['display_state']
        if state not in ReusePreviewPlayer.REUSE_POOLS or row['target_state']!=state:continue
        name=row['asset']
        if name not in cached:
            directory=HERE/'candidates'/name if name.startswith('talking_calm_reuse') else AURA/'assets/avatar'/name
            cached[name]=[]
            for path in sorted(directory.glob('*.png')):
                with Image.open(path) as image:cached[name].append(image.convert('RGBA'))
        frames=cached[name];pos=row['source_position'];index=int(pos);fraction=pos-index
        image=frames[index]
        if fraction and index+1<len(frames):image=Image.blend(image,frames[index+1],fraction)
        if row['alpha']>0:image=Image.blend(image,frames[0],row['alpha'])
        rows.append({'state':state,'t':row['t'],'mouth_pixels':mouth_pixels(image)})
    return closed_runs(rows)


def main():
    core=ReusePreviewPlayer();core.idle_gain=0
    yy,xx=np.mgrid[:480,:464]
    mouth_neutral=((xx+.5-225)/17)**2+((yy+.5-151)/12)**2<=1.08**2
    mouth_emotional=((xx+.5-225)/19)**2+((yy+.5-151)/13)**2<=1.08**2
    outside={state:~(mouth_neutral if state=='SPEAKING_NEUTRAL' else mouth_emotional) for state in core.REUSE_POOLS}
    anchors={name:np.asarray(image).astype(np.int16) for name,image in core._reuse_anchors.items()}
    mouth_rows=[];region_delta=0;alpha_delta=0
    class Inspector(ScriptRunner):
        def _sample(self,t):
            nonlocal region_delta,alpha_delta
            meta=super()._sample(t)
            if meta is not None and meta['display_state'] in core.REUSE_POOLS:
                name=meta['asset'];state=meta['display_state']
                pixels=np.asarray(meta['image']).astype(np.int16)
                delta=np.abs(pixels-anchors[name])
                region_delta=max(region_delta,int(delta[outside[state]].max()))
                alpha_delta=max(alpha_delta,int(delta[:,:,3].max()))
                if meta['target_state']==state:
                    mouth_rows.append({'t':t,'state':state,'asset':name,'mouth_pixels':mouth_pixels(meta['image'])})
            return meta
    runner=Inspector(core,dt=1/30);trace=runner.run(quiet=True)
    assert not trace.errors and not trace.rejected and core.fsm.state.label=='IDLE'
    assert region_delta==0 and alpha_delta==0
    used={state:sorted({row['asset'] for row in mouth_rows if row['state']==state}) for state in core.REUSE_POOLS}
    assert all(set(used[state])==set(names) for state,names in core.REUSE_POOLS.items())
    after=closed_runs(mouth_rows)
    assert all(duration<=.35 for duration in after.values()),after
    stops=[]
    for state,names in core.REUSE_POOLS.items():
        for name in names:
            for phase in range(len(core._reuse_frames[name])-1):
                core.reset_playback();core._asset_of[state]=name
                core._pool_i[state]=names.index(name)
                core.display_frame(state,0)
                duration=phase/24+.01;core.display_frame(state,duration)
                for j in range(16):
                    meta=core.display_frame('IDLE',duration+j/30)
                    if meta['display_state']=='IDLE':stops.append(j/30);break
                else:raise AssertionError((state,name,phase,'stop exceeded .5 seconds'))
    sample_count=len(trace.samples)
    assert sample_count>1900
    runner.reset()
    assert core.frame_at('SPEAKING_NEUTRAL',0)['source_position']==0
    report={'script_seconds':66,'samples':sample_count,
            'all_speaking_pools_used':used,'errors':[],'rejected':[],'final_state':'IDLE',
            'max_outside_mouth_channel_delta':region_delta,'max_alpha_delta':alpha_delta,
            'before_max_closed_seconds':before_measurement(),'after_max_closed_seconds':after,
            'stop_phase_cases':len(stops),'max_display_recovery_seconds':max(stops),
            'note':'30Hz virtual clock, idle micro-motion disabled. Mouth colour count (<5 pixels) is a reviewed visual proxy. Brief speech closures are expected; no audio/phoneme synchronization. Emotional mouths come from their own existing assets.'}
    (HERE/'speech_fix_verification.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(report,indent=2))


if __name__=='__main__':main()
