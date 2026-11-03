from pathlib import Path
H=Path(__file__).resolve().parent;C=H/'candidate_source';A=H.parents[1]/'aura'
def edit(name,old,new):
 p=C/name;s=p.read_text(encoding='utf-8');assert s.count(old)==1,(name,old[:80],s.count(old));p.write_text(s.replace(old,new),encoding='utf-8')
edit('tools/voice_channel_source.py','profile_token=None,visual_exchange=None):','profile_token=None,visual_exchange=None,device_reply=None):')
edit('tools/voice_channel_source.py','    board_exchange=identity_exchange or visual_exchange',"    from tools.device_client import DeviceReplyStream\n    board_exchange=identity_exchange or visual_exchange or (DeviceReplyStream(device_reply) if device_reply else None)")
edit('tools/voice_channel_source.py','    gate=FeedbackGate(plan)',"""    if board_exchange is None:
        from tools.device_client import recall
        from common.device_memory import context_message
        observation=context_message(recall(meta,text))
        if observation is not None and wire_history_within_budget(model,[observation]+history,model_text):
            history=[observation]+history
    gate=FeedbackGate(plan)""")
edit('tools/voice_channel_source.py','def serve_channel(handler, meta, text, timeout, *, recognition_ms=None):','def serve_channel(handler, meta, text, timeout, *, recognition_ms=None,device_reply=None):')
edit('tools/voice_channel_source.py',"    if identity_feature in ('enrollment-v1','enrollment-active-v1'):","    if device_reply is None and identity_feature in ('enrollment-v1','enrollment-active-v1'):")
edit('tools/voice_channel_source.py',"    if identity_exchange is None and handler.headers.get('X-Aura-Visual')", "    if device_reply is None and identity_exchange is None and handler.headers.get('X-Aura-Visual')")
edit('tools/voice_channel_source.py','                            visual_exchange=visual_exchange,','                            visual_exchange=visual_exchange,device_reply=device_reply,')
edit('tools/voice_channel_source.py',"and visual_exchange is None else None)","and visual_exchange is None and device_reply is None and identity_exchange is None else None)")
edit('tools/board_model_host.py',"                remaining=meta['budget_ms']/1000-(time.monotonic()-started)","                from tools.device_client import command\n                device_reply=command(meta,text,pcm)\n                remaining=meta['budget_ms']/1000-(time.monotonic()-started)")
edit('tools/board_model_host.py','serve_channel(self,meta,text,remaining,recognition_ms=round(asr_ms,2))','serve_channel(self,meta,text,remaining,recognition_ms=round(asr_ms,2),device_reply=device_reply)')
edit('tools/board_model_host.py',"        if self.path=='/v1/voice/feedback':", "        if self.path=='/v1/voice/social':\n            self.send(200,{'assets':getattr(self.server.models,'social_assets',{})});return\n        if self.path=='/v1/voice/feedback':")
edit('tools/board_model_host.py','        self.warmed_up=True',"        from tools.social_feedback import prepare as prepare_social\n        try:prepare_social(self)\n        except Exception:self.social_assets={}\n        self.warmed_up=True")
# Generic feedback downloader also validates social clips by their exact hash.
edit('board/runtime/audio/channel_jobs.py','def feedback_cache(config,cache_root):',"def feedback_cache(config,cache_root,*,social=False):")
edit('board/runtime/audio/channel_jobs.py',"    assets=json.loads(get('/v1/voice/feedback',8192)).get('assets',{})\n    if set(assets)!={'thinking'}:raise ValueError('Selected-voice thinking clip is not ready')", "    assets=json.loads(get('/v1/voice/social' if social else '/v1/voice/feedback',8192)).get('assets',{})\n    if set(assets)!=({'arrival','invitation'} if social else {'thinking'}):raise ValueError('Selected-voice cue is not ready')")
edit('board/runtime/audio/channel_jobs.py',"self.feedback_assets={};self.feedback_error='';self.feedback_address=None", "self.feedback_assets={};self.social_assets={};self.feedback_error='';self.feedback_address=None")
edit('board/runtime/audio/channel_jobs.py',"        self.feedback_assets=assets;self.feedback_address=address;self.feedback_error=''", "        self.feedback_assets=assets;self.feedback_address=address;self.feedback_error=''\n        try:self.social_assets=feedback_cache(config,self.feedback_root,social=True)\n        except (OSError,ValueError,RuntimeError):self.social_assets={}")
# Monitor preference remains the master opt-out for microphone and observations.
edit('tools/board_avatar_gtk.py',"                                   'barge_enabled':bool(config.get('voice_barge_in')),", "                                   'barge_enabled':bool(config.get('voice_barge_in')),\n                                   'device_observer':True,'visual_social':True,")

# These features are included in loaded-source verification, not just documents.
p=C/'common/voice_service_capabilities.py';p.write_bytes((A/'common/voice_service_capabilities.py').read_bytes())
edit('common/voice_service_capabilities.py',"SERVICE_REVISION = 'voice-animation-dialogue-20261026-r3'","SERVICE_REVISION = 'voice-device-skills-20261028-r4'")
edit('common/voice_service_capabilities.py',"'audio_clock_animation':1}","'audio_clock_animation':1,'audio_first_wake':1,'bounded_device_context':1}")
edit('common/voice_service_capabilities.py',"SOURCE_FILES = (", "SOURCE_FILES = (\n    'common/voice_wake.py','common/device_memory.py','tools/device_client.py','tools/social_feedback.py',\n    'tools/visual_voice_host.py','tools/visual_question_host.py','common/visual_question.py',")
