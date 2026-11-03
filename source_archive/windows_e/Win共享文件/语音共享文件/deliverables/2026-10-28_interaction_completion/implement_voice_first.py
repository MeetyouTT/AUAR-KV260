from pathlib import Path
HERE=Path(__file__).resolve().parent
ROOT=HERE/'candidate_source'

def replace(path, old, new):
    path=ROOT/path
    text=path.read_text(encoding='utf-8')
    assert text.count(old)==1, (path, old[:100], text.count(old))
    path.write_text(text.replace(old,new),encoding='utf-8')

replace('tools/board_model_host.py', "entry_headers!=['visual-speech-v1']", "entry_headers not in (['visual-speech-v1'],['wake-word-v1'])")
replace('tools/board_model_host.py', "            if entry_headers:\n                from common.handsfree_entry import acceptable_entry", """            if entry_headers==['wake-word-v1']:
                from common.voice_wake import wake_request
                text=wake_request(text)
                if text is None:
                    self.send(422,{'code':'entry_rejected','error':'Wake word not detected'});return
                if not text:
                    self.send_response(204)
                    self.send_header('X-Aura-Entry','wake-word-v1')
                    self.send_header('Content-Length','0')
                    self.send_header('Cache-Control','no-store')
                    self.end_headers()
                    return
            elif entry_headers:
                from common.handsfree_entry import acceptable_entry""")
replace('tools/voice_channel_source.py', "handler.send_header('X-Aura-Entry','visual-speech-v1')", "handler.send_header('X-Aura-Entry',handler.headers['X-Aura-Entry'])")
replace('board/runtime/audio/voice_channel.py', 'visual_entry=False,profile_token=None):', 'visual_entry=False,profile_token=None,wake_entry=False):')
replace('board/runtime/audio/voice_channel.py', "            if visual_entry:headers['X-Aura-Entry']='visual-speech-v1'", """            if visual_entry and wake_entry:raise ValueError('Conflicting entry modes')
            entry_mode='wake-word-v1' if wake_entry else 'visual-speech-v1' if visual_entry else None
            if entry_mode:headers['X-Aura-Entry']=entry_mode""")
replace('board/runtime/audio/voice_channel.py', '            if visual_entry and response.status==422:', '            if entry_mode and response.status==422:')
replace('board/runtime/audio/voice_channel.py', "            if response.status != 200 or response.getheader('Content-Type') != CONTENT_TYPE:", """            if wake_entry and response.status==204:
                if response.getheader('X-Aura-Entry')!='wake-word-v1':
                    raise RuntimeError('Wake response lacks negotiation')
                response.read()
                if self.cancelled.is_set() or not is_current() or time.monotonic()>=deadline:
                    raise InterruptedError('Wake response expired')
                return {'wake_only':True}
            if response.status != 200 or response.getheader('Content-Type') != CONTENT_TYPE:""")
replace('board/runtime/audio/voice_channel.py', "            if visual_entry and response.getheader('X-Aura-Entry')!='visual-speech-v1':", "            if entry_mode and response.getheader('X-Aura-Entry')!=entry_mode:")
replace('board/runtime/audio/channel_jobs.py', 'self.visual_entry_capture=None;self.next_feedback_refresh=0.', 'self.visual_entry_capture=None;self.wake_entry_capture=None;self.next_feedback_refresh=0.')
replace('board/runtime/audio/channel_jobs.py', '    def refresh_feedback(self):', '''    def mark_wake_entry(self,capture_id):
        with self.condition:self.wake_entry_capture=capture_id

    def refresh_feedback(self):''')
replace('board/runtime/audio/channel_jobs.py', '                    def receive(header,payload):', '''                    options={}
                    def receive(header,payload):
                        if header['kind']=='start' and options.get('wake_entry'):
                            self._put(meta,{'wake_detected':True,'wake_only':False})''')
replace('board/runtime/audio/channel_jobs.py', "                    options={}\n                    with self.condition:\n                        if self.visual_entry_capture", "                    with self.condition:\n                        if self.wake_entry_capture==meta['capture_id']:\n                            options['wake_entry']=True;self.wake_entry_capture=None\n                        if self.visual_entry_capture")
replace('board/runtime/audio/channel_jobs.py', "                    self._put(meta,{'network_complete':result})", """                    if result.get('wake_only'):
                        self._put(meta,{'wake_detected':True,'wake_only':True})
                    else:self._put(meta,{'network_complete':result})""")
replace('tools/board_recording.py', "                if result.get('entry_rejected') and hasattr(self,'_entry_rejected'):", """                if result.get('wake_detected') and hasattr(self,'_wake_detected'):
                    self._wake_detected(wake_only=bool(result.get('wake_only')));continue
                if result.get('entry_rejected') and hasattr(self,'_entry_rejected'):""")

# Start from the current board snapshot, not the older shared GUI.
gui=ROOT/'tools/board_avatar_gtk.py'
assert not gui.exists()
gui.write_bytes((HERE/'baseline/tools/board_avatar_gtk.py').read_bytes())
replace('tools/board_avatar_gtk.py', '                    recording_type=BargeInRecordingController', '''                    from tools.voice_first_recording import VoiceFirstRecordingController
                    recording_type=VoiceFirstRecordingController''')
replace('tools/board_avatar_gtk.py', "            elif hf_state=='WAITING_PERSON':", """            elif hf_state=='WAITING_WAKE':status='叫“汐蓝”“欸”或“哎”，我就听你说'
            elif hf_state=='CHECKING_WAKE':status='正在听清唤醒词…'
            elif hf_state=='WAITING_PERSON':""")
replace('tools/board_avatar_gtk.py', "            elif hf_state=='WAITING_SPEECH':status='看见你了，正在等你开口…'", "            elif hf_state=='WAITING_SPEECH':status='我在听，直接说就好…'")
