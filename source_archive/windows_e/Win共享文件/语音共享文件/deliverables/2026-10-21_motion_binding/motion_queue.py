"""Audio-clock gesture decisions, bounded and independent of rendering."""
from common.speech_motion import ACTION_STATES

SPEAKING=frozenset(('SPEAKING','SPEAKING_NEUTRAL','SPEAKING_LOW'))
REACTIONS=frozenset(ACTION_STATES.values())


def decide(control,history,*,sample,state,audible,track,paused):
    """Return apply/wait/skip and a diagnostic reason, without side effects."""
    target=control['at_sample'];action=control.get('action','')
    if sample<target:return 'wait','future_audio'
    if not action:return 'apply','emotion_only'
    if action not in ACTION_STATES:return 'skip','unsupported_action'
    if len(history)>=2:return 'skip','turn_budget'
    if any(row['action']==action for row in history):return 'skip','duplicate_action'
    if not audible or track!='answer' or paused:return 'wait','answer_not_audible'
    # Do not attach a delayed reaction to a different sentence much later.
    if sample-target>36000:return 'skip','expired_audio_cue'
    if history and sample-history[-1].get('started_sample',history[-1]['at_sample'])<96000:
        return 'skip','gesture_spacing'
    if state in REACTIONS:return 'wait','previous_gesture_active'
    if state not in SPEAKING:return 'skip','state_not_speaking'
    return 'apply','audio_cue'
