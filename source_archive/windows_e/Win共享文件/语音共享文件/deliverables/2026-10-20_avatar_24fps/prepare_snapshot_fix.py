from pathlib import Path
HERE=Path(__file__).resolve().parent
base=HERE/'snapshot_baseline/aura/tools';out=HERE/'snapshot_fix_sources/tools';out.mkdir(parents=True,exist_ok=True)
s=(base/'board_recording.py').read_text(encoding='utf-8')
s=s.replace('from board.runtime.audio.capture import Mcp01Capture','from board.runtime.audio.capture import Mcp01Capture, CapturedAudio')
s=s.replace('        self._collect()\n        state = self.controller.public()', '        self._collect()\n        state = self.controller.public()',1)
old='        metadata = self.utterance.metadata() if self.utterance is not None else None'
new="""        # CapturedAudio/AudioRef are frozen and PCM is immutable bytes.
        # Keep only one completed utterance; a new object invalidates the cache.
        utterance=self.utterance
        if isinstance(utterance,CapturedAudio) and isinstance(utterance.pcm,bytes):
            if getattr(self,'_public_utterance',None) is not utterance:
                self._public_utterance=utterance;self._public_metadata=utterance.metadata()
            metadata=dict(self._public_metadata,format=dict(self._public_metadata['format']))
        else:
            self._public_utterance=None
            metadata=utterance.metadata() if utterance is not None else None
        service=self.transcriber.public() if self.transcriber else {'enabled':False,'pending':False}
        playback_active=(state['phase']!='IDLE' or state['playing'] or state['paused']
                         or state.get('pending_job') is not None
                         or state.get('audio_output_state') not in ('NULL','EOS','IDLE_READY'))"""
assert old in s;s=s.replace(old,new)
# Restrict replacements to public(), preserving all control decisions elsewhere.
start=s.index('    def public(self):');end=s.index('    def close(self):',start)
head,body,tail=s[:start],s[start:end],s[end:]
body=body.replace('not self._playback_active()', 'not playback_active')
body=body.replace("service=self.transcriber.public() if self.transcriber else {'enabled':False,'pending':False})", 'service=service)')
body=body.replace("self.transcriber.public().get(","service.get(")
(out/'board_recording.py').write_text(head+body+tail,encoding='utf-8')
s=(base/'board_avatar_worker.py').read_text(encoding='utf-8')
s=s.replace('visual_fps=None):','visual_fps=None, performance_path=None):',1)
s=s.replace("        self.presenter=FramePresenter(native_video,lambda:self.generation,self.condition) if native_video and self.visual_period else None", """        from tools.render_performance import PerformanceRecorder
        performance=PerformanceRecorder(performance_path) if performance_path else None
        self.presenter=FramePresenter(native_video,lambda:self.generation,self.condition,performance) if native_video and self.visual_period else None""")
s=s.replace('self.visual_slot+min(.085,self.visual_period*.85))', "self.visual_slot+min(.085,self.visual_period*.85),\n                                        getattr(self.visual_owner,'phase','UNKNOWN'),\n                                        getattr(getattr(getattr(getattr(self.visual_owner,'core',None),'fsm',None),'state',None),'label','UNKNOWN'),dict(timings))")
s=s.replace('def __init__(self,sink,generation,guard):','def __init__(self,sink,generation,guard,performance=None):')
s=s.replace('        self.guard=guard','        self.guard=guard;self.performance=performance')
s=s.replace('def offer(self,rgb,sequence,generation,deadline):','def offer(self,rgb,sequence,generation,deadline,phase=None,state=None,timings=None):')
s=s.replace('self.pending=(rgb,sequence,generation,deadline)','self.pending=(rgb,sequence,generation,deadline,phase,state,timings or {})')
s=s.replace('deliberate_hold_limit_ms=85)', 'deliberate_hold_limit_ms=85,\n                        performance_log=self.performance.status() if self.performance else None)')
s=s.replace('rgb,sequence,generation,deadline=self.pending;self.pending=None', 'rgb,sequence,generation,deadline,phase,state,timings=self.pending;self.pending=None')
s=s.replace('                    self.presented+=1','                    self.presented+=1\n                    if self.performance:self.performance.observe(phase,state,ended,sequence,timings)')
s=s.replace("        if self.thread.is_alive():raise RuntimeError('Avatar presenter did not stop')", "        if self.thread.is_alive():raise RuntimeError('Avatar presenter did not stop')\n        if self.performance:self.performance.close(time.monotonic())")
s=s.replace('copy.deepcopy(', 'snapshot_copy(')
where=s.index('class AvatarRenderWorker:')
s=s[:where]+'''def snapshot_copy(value):
    """Detach JSON-shaped snapshots without deepcopy's per-scalar dispatch.

    Public state is an acyclic JSON tree. Preserve tuples used by test/log
    clients; unsupported values keep the historical deepcopy behavior.
    """
    kind=type(value)
    if kind is dict:return {k:snapshot_copy(v) for k,v in value.items()}
    if kind is list:return [snapshot_copy(v) for v in value]
    if kind is tuple:return tuple(snapshot_copy(v) for v in value)
    if value is None or kind in (str,int,float,bool,bytes):return value
    return copy.deepcopy(value)

'''+s[where:]
(out/'board_avatar_worker.py').write_text(s,encoding='utf-8')
s=(base/'board_avatar_gtk.py').read_text(encoding='utf-8')
old="visual_fps=config.get('stable_avatar_fps',8) if config.get('native_avatar') else None)"
assert old in s
s=s.replace(old,"visual_fps=config.get('stable_avatar_fps',8) if config.get('native_avatar') else None,performance_path=self.evidence_root/'render_performance.jsonl')")
(out/'board_avatar_gtk.py').write_text(s,encoding='utf-8')
source=(HERE/'prepare_action_candidate.py').read_text(encoding='utf-8')
source=source.replace("HERE/'action_sources'","HERE/'snapshot_fix_sources'").replace("'f8e48486023d'","'bd9e48cc658f'")
source=source.replace("'action_candidate.json'","'snapshot_fix_candidate.json'")
source=source.replace(",'tools/board_avatar_worker.py'",'')
exec(compile(source,str(HERE/'prepare_action_candidate.py'),'exec'))
