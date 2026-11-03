"""Exercise actual shared playback/FSM with the candidate; record practical limits."""
import json
from pathlib import Path
import numpy as np
from PIL import Image

from preview_script import AvatarPlayer,ReusePreviewPlayer,ScriptRunner

HERE=Path(__file__).resolve().parent


def thumbnail(image):
    bg=Image.new('RGBA',image.size,(252,252,243,255))
    bg.alpha_composite(image)
    return np.asarray(bg.convert('RGB').resize((116,120),Image.Resampling.BILINEAR),dtype=np.int16)


def main():
    out={'neutral_comparison':{},'stop_cases':[]}
    for label,core in [('original',AvatarPlayer()),('reuse',ReusePreviewPlayer())]:
        core.idle_gain=0
        core.reply_text='A sufficiently long neutral reply for a repeated playback comparison.'
        prev=None;body=[];full=[]
        for i in range(721):
            meta=core.display_frame('SPEAKING_NEUTRAL',i/30)
            assert meta is not None
            frame=thumbnail(meta['image'])
            if prev is not None:
                delta=np.abs(frame-prev)
                full.append(float(delta.mean()))
                # y200..480 in target image; contains both hands and garment.
                body.append(float(delta[50:].mean()))
            prev=frame
        out['neutral_comparison'][label]={'samples':721,'duration_seconds':24,'sample_hz':30,
            'max_body_mad_0_255':max(body),'max_full_mad_0_255':max(full)}
    assert out['neutral_comparison']['reuse']['max_body_mad_0_255']==0
    for duration in (.05,.2,1.0,3.4,23.0):
        core=ReusePreviewPlayer();core.idle_gain=0
        now=0.0
        while now<duration:
            core.display_frame('SPEAKING_NEUTRAL',now)
            now+=1/30
        core.display_frame('SPEAKING_NEUTRAL',duration)
        stopped_at=duration
        for j in range(31):
            meta=core.display_frame('IDLE',duration+j/30)
            assert meta is not None
            if meta['display_state']=='IDLE':
                out['stop_cases'].append({'spoken_seconds':duration,'display_recovered_seconds':j/30})
                break
        else:raise AssertionError('Recovery exceeded 1 second')
    core=ReusePreviewPlayer();core.idle_gain=0
    sweep=[];stop_body_delta=0
    anchor=np.asarray(core._reuse_frames[core.CANDIDATE][0]).astype(np.int16)
    yy,xx=np.mgrid[:480,:464]
    outside=((xx+.5-225)/17)**2+((yy+.5-151)/12)**2>1.08**2
    for asset in (core.CANDIDATE,core.VARIANT):
        for i in range(len(core._reuse_frames[asset])-1):
            core.reset_playback()
            # Select the initial variant directly, then exercise the public display/stop path.
            core._asset_of['SPEAKING_NEUTRAL']=asset
            core.display_frame('SPEAKING_NEUTRAL',0)
            duration=i/24+.01
            core.display_frame('SPEAKING_NEUTRAL',duration)
            for j in range(16):
                meta=core.display_frame('IDLE',duration+j/30)
                if meta['display_state']=='SPEAKING_NEUTRAL':
                    delta=np.abs(np.asarray(meta['image']).astype(np.int16)-anchor)
                    stop_body_delta=max(stop_body_delta,int(delta[outside].max()))
                if meta['display_state']=='IDLE':
                    sweep.append(j/30);break
            else:raise AssertionError('Mouth recovery exceeded half a second: '+asset)
    out['all_phase_stop_sweep']={'cases':len(sweep),'max_recovery_seconds':max(sweep),'sample_hz':30}
    assert stop_body_delta==0
    out['stop_max_outside_mouth_channel_delta']=stop_body_delta
    core=ReusePreviewPlayer();core.idle_gain=0
    runner=ScriptRunner(core,dt=1/30,sample_every=.5)
    trace=runner.run(quiet=True)
    assert not trace.errors and not trace.rejected
    reused=[r for r in trace.samples if r.get('asset') in (core.CANDIDATE,core.VARIANT)]
    assert reused and all(r.get('display_state')=='SPEAKING_NEUTRAL' for r in reused)
    assert {r['asset'] for r in reused}=={core.CANDIDATE,core.VARIANT}
    assert core.fsm.state.label=='IDLE'
    sample_count=len(trace.samples)
    runner.reset()
    assert not runner.trace.errors and not runner.trace.samples
    assert core.frame_at('SPEAKING_NEUTRAL',0)['source_position']==0
    out['script']={'duration_seconds':66,'samples':sample_count,
                   'errors':[],'rejected':[],'reused_asset_samples':len(reused),
                   'both_mouth_variants_used':True,
                   'final_state':'IDLE','reset_restarts_from_first_frame':True}
    out['measurement_note']='MAD is a 116x120 RGB diagnostic, not a perceptual score. Idle micro-motion disabled for comparison. This file checks neutral speech; all three moods are covered by verify_speech_fix.py. No audio synthesis or phoneme sync.'
    (HERE/'playback_verification.json').write_text(json.dumps(out,indent=2),encoding='utf-8')
    print(json.dumps(out,indent=2))


if __name__=='__main__':main()
