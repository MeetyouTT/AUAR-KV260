"""Line-protocol audio worker. EOF/close/stop release only this worker's audio."""
import argparse
from collections import deque
import errno
import os
import json
from pathlib import Path
import queue
import sys
import threading
import time

AURA = Path(__file__).resolve().parents[1]
if str(AURA) not in sys.path:
    sys.path.insert(0, str(AURA))
from tools.gstreamer_audio_engine import GstAudioEngine, REQUIRED_ELEMENTS


def emit(message):
    print('AUDIO ' + json.dumps(message, ensure_ascii=False), flush=True)


class NonBlockingAudioPublisher:
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
                self.pending=('AUDIO '+json.dumps(message,ensure_ascii=False)+'\n').encode('utf-8');self.offset=0
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


def load_gst():
    import gi
    gi.require_version('Gst', '1.0')
    from gi.repository import Gst, GLib
    Gst.init(None)
    missing = [name for name in REQUIRED_ELEMENTS if Gst.ElementFactory.find(name) is None]
    if missing:
        raise RuntimeError('Missing GStreamer elements: ' + ', '.join(missing))
    return Gst, GLib


def _idle_state_key(engine, state):
    # IDLE_READY is the persistent engine's inactive state, not WAITING_PCM.
    # Nonpersistent engines have no active attribute and retain every tick.
    if (getattr(engine, 'active', True) is not False
            or getattr(engine, 'paused', False) is True
            or state.get('persistent') is not True
            or state.get('device_ready') is not True
            or state.get('device_state') != 'IDLE_READY'
            or state.get('audible') is not False
            or state.get('error')):
        return None
    # Clocks, timers and diagnostic/IPC counters are not logical idle changes.
    return tuple(state.get(name) for name in (
        'token', 'ready', 'done', 'error', 'device_ready', 'device_state',
        'audible', 'track', 'duration', 'device', 'output_caps', 'clock_source'))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--device', default='hw:CARD=MCP01,DEV=0')
    parser.add_argument('--probe', action='store_true', help='Initialize libraries and list plugins; no device playback')
    parser.add_argument('--persistent', action='store_true')
    parser.add_argument('--echo-reference',action='store_true')
    args = parser.parse_args(argv)
    try:
        gst, glib = load_gst()
    except Exception as exc:
        emit({'kind': 'boot', 'error': type(exc).__name__ + ': ' + str(exc)})
        return 1
    if args.probe:
        print(json.dumps({'status': 'PASS', 'version': gst.version_string(),
                          'elements': list(REQUIRED_ELEMENTS), 'device_opened': False}))
        return 0
    publisher=NonBlockingAudioPublisher()
    def publish(message):
        publisher.publish(message);publisher.flush()
    if args.persistent:
        from tools.gstreamer_persistent_engine import PersistentGstAudioEngine
        engine = None
        try:
            engine=PersistentGstAudioEngine(gst,args.device)
            deadline=time.monotonic()+8
            while not engine.poll()['device_ready']:
                if engine.error or time.monotonic()>=deadline:raise RuntimeError(engine.error or 'Persistent audio warmup timed out')
                time.sleep(.01)
        except Exception as exc:
            if engine is not None:engine.release()
            publish({'kind':'boot','error':type(exc).__name__+': '+str(exc)})
            return 1
    else:engine = GstAudioEngine(gst, args.device)
    loop = glib.MainLoop()
    commands = queue.Queue(maxsize=32)
    eof = threading.Event()
    last_idle_key = last_idle_published_at = None

    def receive():
        try:
            for line in sys.stdin:
                if len(line) > 8192:
                    eof.set()
                    return
                try:
                    message = json.loads(line)
                    if not isinstance(message, dict):
                        raise ValueError('Expected command object')
                    commands.put(message, timeout=1)
                except (ValueError, queue.Full):
                    eof.set()
                    return
        finally:
            eof.set()

    def tick():
        nonlocal last_idle_key, last_idle_published_at
        command_received = False
        try:
            for _ in range(16):
                try:
                    message = commands.get_nowait()
                except queue.Empty:
                    break
                command_received = True
                if engine.command(message) and message['type'] == 'close':
                    loop.quit()
                    return False
            if publisher.broken or eof.is_set() and commands.empty():
                engine.release()
                loop.quit()
                return False
            state = engine.poll()  # Preserve the original 10ms audio/sink work.
            idle_key = _idle_state_key(engine, state)
            now = time.monotonic()
            if (idle_key is None or command_received or idle_key != last_idle_key
                    or last_idle_published_at is None
                    or not 0 <= now - last_idle_published_at < 1.):
                publish(dict(state, kind='state', ipc=publisher.snapshot()))
                last_idle_key = idle_key
                last_idle_published_at = now if idle_key is not None else None
            else:
                publisher.flush()  # Finish a previous partial/nonblocking write.
            if args.echo_reference and hasattr(engine,'take_references'):
                import base64
                for frame in engine.take_references():
                    frame=dict(frame,kind='reference',pcm=base64.b64encode(frame['pcm']).decode('ascii'))
                    publish(frame)
        except (BrokenPipeError, OSError):
            engine.release()
            loop.quit()
            return False
        except Exception as exc:
            last_idle_key = last_idle_published_at = None
            engine.fail(type(exc).__name__ + ': ' + str(exc))
            publish(dict(engine.snapshot(), kind='state'))
        return True

    publish({'kind': 'boot', 'device': args.device, 'error': ''})
    threading.Thread(target=receive, daemon=True, name='aura-gst-commands').start()
    glib.timeout_add(10, tick)
    try:
        loop.run()
    finally:
        engine.release()
    return 0


if __name__ == '__main__':
    sys.exit(main())
