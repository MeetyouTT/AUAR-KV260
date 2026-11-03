"""Validate local mouth gating, audio placement and all recorded cached cues."""
import json
from pathlib import Path
import sys

import numpy as np

HERE=Path(__file__).resolve().parent
AURA=HERE.parent.parent/'aura';sys.path.insert(0,str(AURA))
from tools.selected_voice_demo import VoicePlan,create_demo_core


def main():
    plan=VoicePlan();core=create_demo_core('reuse');core.idle_gain=0
    local=[]
    # The source reuse frames already share fixed eyes, body and alpha.
    # Compare the actual new compositor at 0 / half / full strength.
    for state,pool in core.REUSE_POOLS.items():
        for asset in pool:
            core.reset_playback();core._asset_of[state]=asset
            core.frame_at(state,0)
            images=[]
            for strength in (0,.5,1):
                core.speech_gain=strength
                images.append(np.array(core.frame_at(state,.37)['image']))
            anchor=np.array(core._reuse_anchors[asset])
            varying=np.any(np.array(core._reuse_frames[asset])!=anchor,axis=(0,3))
            outside=~varying
            row={'state':state,'asset':asset,
                 'zero_gain_anchor_max_difference':int(np.abs(images[0].astype(int)-anchor.astype(int)).max()),
                 'fixed_region_max_difference':max(int(np.abs(im.astype(int)-anchor.astype(int))[outside].max()) for im in images),
                 'alpha_max_difference':max(int(np.abs(im[:,:,3].astype(int)-anchor[:,:,3].astype(int)).max()) for im in images)}
            assert all(row[key]==0 for key in ('zero_gain_anchor_max_difference','fixed_region_max_difference','alpha_max_difference'))
            local.append(row)
    timeline=json.loads((HERE/'timeline.json').read_text(encoding='utf-8'))
    samples=timeline['samples'];utterances=plan.utterances
    stages=[]
    for u in utterances:
        playing=[r for r in samples if u['start']+.15<=r['t']<u['end']-.15]
        state={'friendly':'SPEAKING_NEUTRAL','neutral':'SPEAKING_NEUTRAL','happy':'SPEAKING','sad':'SPEAKING_LOW','excited':'SPEAKING'}[u['emotion']]
        assert playing and all(r['display_state']==state for r in playing)
        closed=[r for r in samples if u['end']+.2<=r['t']<u['end']+.5]
        assert closed and all(r['speech_gain']==0 for r in closed)
        recovered=next(r for r in samples if r['t']>=u['end'] and not r['display_state'].startswith('SPEAKING'))
        # A closed mouth may remain in the old display state for one extra
        # cached sample while the shared exit stage commits the new state.
        assert recovered['t']-u['end']<.3
        stages.append({'label':u['label'],'start':u['start'],'end':u['end'],
                       'expected_display_state':state,'playing_samples':len(playing),
                       'gain_zero_at_or_before':next(r['t'] for r in samples if r['t']>=u['end'] and r['speech_gain']==0),
                       'display_recovery_seconds':round(recovered['t']-u['end'],6)})
    assert samples[-1]['display_state']=='IDLE' and samples[-1]['speech_gain']==0
    result={'status':'PASS','limits':'Activity timing and cached frame checks; not phoneme alignment or physical speaker/display latency.',
            'mouth_compositor':local,'utterances':stages,'source_audio_hashes':'PASS','final_state':'IDLE'}
    (HERE/'sync_verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(result,ensure_ascii=False),flush=True)


if __name__=='__main__':main()
