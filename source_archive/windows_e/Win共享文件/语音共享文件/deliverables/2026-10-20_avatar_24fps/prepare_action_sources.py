"""Produce a reviewable overlay; do not edit concurrent production sources."""
from pathlib import Path
import shutil

HERE=Path(__file__).resolve().parent
APP=HERE.parents[1]/'aura'
OUT=HERE/'action_sources'

def save(name,text):
    path=OUT/name
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(text,encoding='utf-8')

save('common/speech_motion.py',(APP/'common/speech_motion.py').read_text(encoding='utf-8'))
text=(APP/'common/voice_channel.py').read_text(encoding='utf-8')
text=text.replace("import struct\n", "import struct\nfrom common.speech_motion import ACTION_STATES\n")
text=text.replace("header.get('action') not in {'', 'ack_nod', 'deny_shake'}", "header.get('action') not in {'', *ACTION_STATES}")
save('common/voice_channel.py',text)

text=(APP/'tools/voice_channel_source.py').read_text(encoding='utf-8')
text=text.replace('identity_exchange=None,conversation=None):', 'identity_exchange=None,conversation=None,motion=False):')
text=text.replace('from common.spoken_input import prepare_spoken_input', 'from common.spoken_input import prepare_spoken_input\nfrom common.speech_motion import SpeechMotionPlan')
text=text.replace('    owner = ChannelWriter(meta)', '    owner = ChannelWriter(meta)\n    motion_plan = SpeechMotionPlan()')
text=text.replace('latency_options=latency)', "latency_options=latency,speech_motion='v1' if motion else 'disabled')")
old="            while True:\n                pcm = audio.readframes(PACKET_SAMPLES)"
new="""            # Cue precedes its PCM, so the board can apply it at audible time.
            # This also works when reply metadata arrives after the first sentence.
            if motion:
                cue=motion_plan.cue(part, owner.state.samples,
                                   emotion=reply.get('emotion') if reply else None,
                                   action=reply.get('avatar_action','') if reply else '')
                yield owner.frame('control', **cue, tone_applied=False)
            while True:
                pcm = audio.readframes(PACKET_SAMPLES)"""
assert old in text
text=text.replace(old,new)
text=text.replace("conversation=(handler.headers['X-Aura-Conversation'][3:] if handler.headers.get('X-Aura-Conversation') else None))", "conversation=(handler.headers['X-Aura-Conversation'][3:] if handler.headers.get('X-Aura-Conversation') else None),\n                            motion=handler.headers.get('X-Aura-Motion')=='speech-v1')")
save('tools/voice_channel_source.py',text)

text=(APP/'board/runtime/audio/voice_channel.py').read_text(encoding='utf-8')
text=text.replace("headers={'Content-Type':'application/octet-stream','X-Aura-Asr':encode_context(meta)}", "headers={'Content-Type':'application/octet-stream','X-Aura-Asr':encode_context(meta),\n                     'X-Aura-Motion':'speech-v1'}")
save('board/runtime/audio/voice_channel.py',text)

text=(APP/'board/runtime/fsm.py').read_text(encoding='utf-8')
old='        # 播报结束（三档共用同一事件）'
assert old in text
text=text.replace(old,"""        # Validated stream cues can arrive during an already audible answer.
        for speaking in (S.SPEAKING, S.SPEAKING_NEUTRAL, S.SPEAKING_LOW):
            T[(speaking, EventType.DIALOGUE_RESPONSE_RECEIVED)] = S.SPEAKING

"""+old)
save('board/runtime/fsm.py',text)

text=(HERE/'stable_fps_sources/streaming_controller.py').read_text(encoding='utf-8')
text=text.replace('from tools.realtime_controller import RealtimeController', 'from tools.realtime_controller import RealtimeController\nfrom common.speech_motion import ACTION_STATES')
text=text.replace("'requested_at':requested_at,'response_applied':False,'controls':[]}", "'requested_at':requested_at,'response_applied':False,'controls':[],\n                         'actions':[], 'puzzled_visible_at':None}")
text=text.replace("elif kind=='control':stream['controls'].append(header)", """elif kind=='control':
            if len(stream['controls'])<32:stream['controls'].append(dict(header))""")
old="""        for control in list(stream['controls']):
            if snapshot.get('answer_clock',0)*24000>=control['at_sample']:
                self.core.emotion=control['emotion'];stream['controls'].remove(control)"""
new="""        for control in list(stream['controls']):
            if snapshot.get('answer_clock',0)*24000<control['at_sample']:continue
            action=control.get('action','')
            # A feedback clock, buffered PCM or paused output is not an audible answer.
            if action and (not snapshot.get('audible') or snapshot.get('track')!='answer'
                           or self.output.paused):continue
            self.core.emotion=control['emotion']
            speaking=self.core.fsm.state.label in {'SPEAKING','SPEAKING_NEUTRAL','SPEAKING_LOW'}
            previous=stream['actions']
            allowed=(action in ACTION_STATES and len(previous)<2
                     and action not in {item['action'] for item in previous}
                     and (not previous or control['at_sample']-previous[-1]['at_sample']>=96000))
            if speaking and (allowed or not action):
                self.core.apply_response({'reply_text':self.reply,'emotion':control['emotion'],
                                          'avatar_action':action if allowed else ''})
                if allowed:
                    previous.append(dict(action=action,at_sample=control['at_sample']))
                    self.record('speech_action_started',action=action,at_sample=control['at_sample'],
                                answer_clock=snapshot.get('answer_clock'),generation=stream['generation'])
            stream['controls'].remove(control)
        # The puzzled asset is a loop; bound its visible reaction, then resume speech.
        if (stream['puzzled_visible_at'] is not None
                and self.now()-stream['puzzled_visible_at']>=.9
                and self.core.fsm.state.label=='PUZZLED'):
            self.send(E.AUDIO_PLAYBACK_START,{'emotion':self.core.emotion})
            stream['puzzled_visible_at']=None"""
assert old in text
text=text.replace(old,new)
text=text.replace("'server_metrics':stream.get('server_metrics',{}),", "'server_metrics':stream.get('server_metrics',{}),'actions':list(stream['actions']),")
text=text.replace("        if self.core.take_burst_finished():", """        if (meta and meta.get('display_state')=='PUZZLED'
                and stream['puzzled_visible_at'] is None):stream['puzzled_visible_at']=self.now()
        if self.core.take_burst_finished():""")
save('tools/streaming_controller.py',text)
print(OUT)
