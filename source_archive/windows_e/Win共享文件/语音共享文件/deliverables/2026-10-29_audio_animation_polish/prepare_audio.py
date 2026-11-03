"""Stage nonblocking audio telemetry; no live source or device changes."""
import json,shutil
from pathlib import Path
H=Path(__file__).resolve().parent
assert not (H/'candidate/board/tools/gstreamer_audio_worker.py').exists()
for name in ('tools/gstreamer_audio_worker.py','tools/gstreamer_persistent_engine.py','tools/realtime_controller.py','tools/streaming_controller.py'):
 target=H/'candidate/board'/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(H/'board_source'/name,target)
# The already captured active interruption code is byte-pinned to the same run.
name='tools/barge_in_capture.py';target=H/'candidate/board'/name
shutil.copy2(H.parent/'2026-10-29_self_interrupt/board_source'/name,target)
path=H/'candidate/board/tools/gstreamer_audio_worker.py';source=path.read_text(encoding='utf-8')
source=source.replace('import argparse\n','import argparse\nfrom collections import deque\nimport errno\nimport os\n',1)
publisher='''class NonBlockingAudioPublisher:
    """Keep pipe backpressure off the GStreamer clock thread.

    Only one latest state and eight reference packets are retained. Never
    discard or alter content PCM; these messages are diagnostic/reference IPC.
    Reference sequence gaps make the existing echo path reject untrusted input.
    """
    def __init__(self, fd=1, *, clock=time.monotonic, write=os.write, configure_fd=True):
        self.fd,self.clock,self.write=fd,clock,write
        if configure_fd:os.set_blocking(fd,False)
        self.boot=None;self.state=None;self.references=deque()
        self.pending=b'';self.offset=0;self.reference_run=0;self.broken=False
        self.blocked_writes=0;self.coalesced_states=0;self.dropped_references=0;self.messages=0

    def publish(self, message):
        kind=message.get('kind')
        if kind=='reference':
            if len(self.references)>=8:self.references.popleft();self.dropped_references+=1
            self.references.append(dict(message))
        elif kind=='boot':self.boot=dict(message)
        else:
            if self.state is not None:self.coalesced_states+=1
            self.state=dict(message)

    def _next(self):
        if self.boot is not None:
            message,self.boot=self.boot,None;return message
        # Reserve fresh clocks/status even during the permanent silence stream.
        if self.state is not None and (self.reference_run>=2 or not self.references):
            message,self.state=self.state,None;self.reference_run=0;return message
        while self.references:
            message=self.references.popleft()
            # A reference which arrives after its queued sound is unsafe for
            # interruption. Drop it; preserve its sequence gap, never relabel.
            if self.clock()-message['at']>.05:
                self.dropped_references+=1;continue
            self.reference_run+=1;return message
        if self.state is not None:
            message,self.state=self.state,None;self.reference_run=0;return message
        return None

    def flush(self):
        for _ in range(16):
            if self.broken:return
            if not self.pending:
                message=self._next()
                if message is None:return
                self.pending=('AUDIO '+json.dumps(message,ensure_ascii=False)+'\\n').encode('utf-8');self.offset=0
            try:
                written=self.write(self.fd,self.pending[self.offset:])
                if written<=0:raise BrokenPipeError('Audio IPC closed')
            except BlockingIOError:
                self.blocked_writes+=1;return
            except OSError as exc:
                if exc.errno in (errno.EAGAIN,errno.EWOULDBLOCK):self.blocked_writes+=1;return
                self.broken=True;return
            self.offset+=written
            if self.offset==len(self.pending):self.pending=b'';self.offset=0;self.messages+=1

    def snapshot(self):
        return {'nonblocking':True,'blocked_writes':self.blocked_writes,
                'coalesced_states':self.coalesced_states,'dropped_references':self.dropped_references,
                'pending_reference_packets':len(self.references),'pending_bytes':len(self.pending)-self.offset,
                'messages':self.messages,'broken_pipe':self.broken}


'''
source=source.replace('def load_gst():',publisher+'def load_gst():',1)
source=source.replace("    if args.persistent:\n", "    publisher=NonBlockingAudioPublisher()\n    def publish(message):\n        publisher.publish(message);publisher.flush()\n    if args.persistent:\n",1)
# Pre-initialization errors and --probe keep the original tiny boot output.
start=source.index('    publisher=NonBlockingAudioPublisher()')
source=source[:start]+source[start:].replace('            emit(', '            publish(').replace('    emit(', '    publish(')
source=source.replace("            if eof.is_set() and commands.empty():", "            if publisher.broken or eof.is_set() and commands.empty():",1)
source=source.replace("publish(dict(engine.poll(), kind='state'))", "publish(dict(engine.poll(), kind='state', ipc=publisher.snapshot()))",1)
assert "print('AUDIO" not in source[start:]
compile(source,str(path),'exec');path.write_text(source,encoding='utf-8')
path=H/'candidate/board/tools/gstreamer_persistent_engine.py';source=path.read_text(encoding='utf-8')
source=source.replace("        self.underrun_packets=0;self.last_data_end=None", "        self.underrun_packets=0;self.turn_underrun_packets=0;self.last_data_end=None\n        self.queued_samples=0;self.last_poll_at=None;self.max_poll_gap_ms=0.;self.turn_late_rebases=0",1)
source=source.replace("        self.started_at=self.answer_started_at=self.last_data_end=None", "        self.started_at=self.answer_started_at=self.last_data_end=None\n        self.queued_samples=0;self.turn_underrun_packets=0;self.max_poll_gap_ms=0.;self.turn_late_rebases=0",1)
source=source.replace("            self.queue.append((part,track,self.input_samples,self.answer_samples))", "            self.queue.append((part,track,self.input_samples,self.answer_samples));self.queued_samples+=len(part)//2",1)
source=source.replace("        if self.pipeline is None:return self.snapshot()\n        gst=self.gst", "        if self.pipeline is None:return self.snapshot()\n        now=self.clock()\n        if self.last_poll_at is not None and self.active and self.ready:\n            self.max_poll_gap_ms=max(self.max_poll_gap_ms,(now-self.last_poll_at)*1000)\n        self.last_poll_at=now\n        gst=self.gst",1)
source=source.replace("        if self.next_pts+100000000<running:\n", "        if self.next_pts+100000000<running:\n            if self.active and self.ready:self.turn_late_rebases+=1\n",1)
source=source.replace("                count=len(pcm)//2;duration=count*gst.SECOND//RATE", "                count=len(pcm)//2;self.queued_samples-=count;duration=count*gst.SECOND//RATE",1)
source=source.replace("if self.active and self.ready and not self.paused and not self.final:self.underrun_packets+=1", "if self.active and self.ready and not self.paused and not self.final:\n                    self.underrun_packets+=1;self.turn_underrun_packets+=1",1)
source=source.replace("'underrun_packets':self.underrun_packets}", "'underrun_packets':self.underrun_packets,\n                'turn_underrun_packets':self.turn_underrun_packets,'queued_ms':round(self.queued_samples*1000/RATE,2),\n                'max_poll_gap_ms':round(self.max_poll_gap_ms,2),'turn_late_rebases':self.turn_late_rebases}")
compile(source,str(path),'exec');path.write_text(source,encoding='utf-8')
path=H/'candidate/board/tools/realtime_controller.py';source=path.read_text(encoding='utf-8')
source=source.replace("                'log':self.log[-30:],'turns':self.turns[-20:],'metrics':dict(self.metrics)}", "                'log':self.log[-30:],'turns':self.turns[-20:],'metrics':dict(self.metrics),\n                'audio_output':{key:value for key,value in self.output.read().items() if key in\n                    ('device_state','underrun_packets','turn_underrun_packets','queued_ms','max_poll_gap_ms','turn_late_rebases','ipc')}}")
compile(source,str(path),'exec');path.write_text(source,encoding='utf-8')
path=H/'candidate/board/tools/streaming_controller.py';source=path.read_text(encoding='utf-8')
source=source.replace("'server_metrics':stream.get('server_metrics',{}),'actions':list(stream['actions']),", "'server_metrics':stream.get('server_metrics',{}),'actions':list(stream['actions']),\n                              'audio_output':{k:v for k,v in snapshot.items() if k in\n                                ('underrun_packets','turn_underrun_packets','max_poll_gap_ms','turn_late_rebases','ipc')},")
compile(source,str(path),'exec');path.write_text(source,encoding='utf-8')
path=H/'candidate/board/tools/barge_in_capture.py';source=path.read_text(encoding='utf-8')
source=source.replace("                if not self.echo.healthy():\n", "                if getattr(self.echo,'reference_gaps',0):\n                    raise RuntimeError('Echo reference discontinuity; keep playback and rearm normal listening')\n                if not self.echo.healthy():\n",1)
compile(source,str(path),'exec');path.write_text(source,encoding='utf-8')
(H/'PROGRESS.json').write_text(json.dumps({'status':'AUDIO_CANDIDATE_STAGED','complete':False,
 'tasks':['continuous speech','existing animation material richness'],'candidate_deployed':False,
 'barge_in_false_positive_user_report_resolved':True,'microphone_enabled_by_agent':False},indent=2),encoding='utf-8')
print('Audio candidate staged; no live files changed')
