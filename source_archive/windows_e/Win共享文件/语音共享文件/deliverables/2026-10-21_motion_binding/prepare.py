from pathlib import Path
HERE=Path(__file__).resolve().parent
out=HERE/'candidate_sources/tools';out.mkdir(parents=True,exist_ok=True)
(out/'motion_queue.py').write_bytes((HERE/'motion_queue.py').read_bytes())
s=(HERE/'baseline/aura/tools/streaming_controller.py').read_text(encoding='utf-8')
s=s.replace('from common.speech_motion import ACTION_STATES','from common.speech_motion import ACTION_STATES\nfrom tools.motion_queue import decide')
s=s.replace("'actions':[], 'puzzled_visible_at':None}","'actions':[], 'motion_events':[], 'puzzled_visible_at':None}")
s=s.replace("if len(stream['controls'])<32:stream['controls'].append(dict(header))", """if len(stream['controls'])<32:stream['controls'].append(dict(header))
            else:self.record('speech_action_skipped',reason='control_queue_full',action=header.get('action',''))""")
start=s.index("        for control in list(stream['controls']):")
end=s.index('        # The puzzled asset',start)
s=s[:start]+'''        for control in list(stream['controls']):
            sample=max(0,round(snapshot.get('answer_clock',0)*24000))
            decision,reason=decide(control,stream['actions'],sample=sample,
                state=self.core.fsm.state.label,audible=snapshot.get('audible',False),
                track=snapshot.get('track'),paused=self.output.paused)
            if decision=='wait':continue
            action=control.get('action','')
            if decision=='apply':
                self.core.emotion=control['emotion']
                if self.core.fsm.state.label in {'SPEAKING','SPEAKING_NEUTRAL','SPEAKING_LOW'}:
                    self.core.apply_response({'reply_text':self.reply,'emotion':control['emotion'],
                                              'avatar_action':action})
                    if action:
                        stream['actions'].append(dict(action=action,at_sample=control['at_sample'],
                                                       started_sample=sample))
                        self.record('speech_action_started',action=action,at_sample=control['at_sample'],
                                    answer_clock=snapshot.get('answer_clock'),generation=stream['generation'])
            if action:
                event=dict(action=action,at_sample=control['at_sample'],observed_sample=sample,
                           outcome=decision,reason=reason)
                stream['motion_events'].append(event);stream['motion_events']=stream['motion_events'][-16:]
                if decision=='skip':self.record('speech_action_skipped',**event)
            stream['controls'].remove(control)
''' +s[end:]
s=s.replace("self.send(E.AUDIO_PLAYBACK_START,{'emotion':self.core.emotion})\n            stream['puzzled_visible_at']=None", "self.send(E.AUDIO_PLAYBACK_START,{'emotion':self.core.emotion})\n            stream['puzzled_visible_at']=None")
s=s.replace("and stream['puzzled_visible_at'] is None):", "and self.core.fsm.state.label=='PUZZLED'\n                and stream['puzzled_visible_at'] is None):")
s=s.replace("'actions':list(stream['actions']),", "'actions':list(stream['actions']),\n                              'motion_events':list(stream['motion_events']),")
s=s.replace("if self.stream:state['thinking_feedback']=self.stream['hint']", """if self.stream:
            state['thinking_feedback']=self.stream['hint']
            state['speech_motion']={'pending':len(self.stream['controls']),
                'actions':[dict(row) for row in self.stream['actions']],
                'events':[dict(row) for row in self.stream['motion_events']]}""")
(out/'streaming_controller.py').write_text(s,encoding='utf-8')
print('Candidate sources prepared; production unchanged')
