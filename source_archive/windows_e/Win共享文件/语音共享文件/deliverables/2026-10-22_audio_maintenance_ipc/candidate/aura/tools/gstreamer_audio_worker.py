"""Original audio worker with explicitly enabled idle maintenance IPC."""
import argparse
import base64
import json
from pathlib import Path
import queue
import sys
import threading
import time

AURA=Path(__file__).resolve().parents[1]
if str(AURA) not in sys.path:sys.path.insert(0,str(AURA))
from tools.gstreamer_audio_engine import GstAudioEngine,REQUIRED_ELEMENTS


def emit(message):
    print('AUDIO '+json.dumps(message,ensure_ascii=False,allow_nan=False),flush=True)


def load_gst():
    import gi
    gi.require_version('Gst','1.0')
    from gi.repository import Gst,GLib
    Gst.init(None)
    missing=[name for name in REQUIRED_ELEMENTS if Gst.ElementFactory.find(name) is None]
    if missing:raise RuntimeError('Missing GStreamer elements: '+', '.join(missing))
    return Gst,GLib


def synthetic_pipeline(gst,device):
    if device!='SYNTHETIC_FAKESINK_NO_ALSA':raise ValueError('Explicit synthetic identifier required')
    pipeline=gst.parse_launch('appsrc name=source is-live=true format=time block=false '
        'caps=audio/x-raw,format=S16LE,layout=interleaved,rate=24000,channels=1 '
        '! audioconvert ! fakesink name=sink sync=true')
    return pipeline,pipeline.get_by_name('source'),pipeline.get_by_name('sink')


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--device',default='hw:CARD=MCP01,DEV=0')
    parser.add_argument('--probe',action='store_true')
    parser.add_argument('--persistent',action='store_true')
    parser.add_argument('--echo-reference',action='store_true')
    parser.add_argument('--maintenance-instance')
    parser.add_argument('--maintenance-fakesink',action='store_true')
    args=parser.parse_args(argv)
    instance=args.maintenance_instance
    if instance is not None:
        from tools.audio_maintenance_wire import HEX32
        if not HEX32.fullmatch(instance) or not args.persistent:
            parser.error('Maintenance requires persistent audio and a 32-hex worker instance')
    if args.maintenance_fakesink and (not instance or args.device!='SYNTHETIC_FAKESINK_NO_ALSA'):
        parser.error('Synthetic sink requires maintenance instance and explicit synthetic identifier')
    if args.device=='SYNTHETIC_FAKESINK_NO_ALSA' and not args.maintenance_fakesink:
        parser.error('Synthetic identifier cannot open a hardware device')

    def boot(error=''):
        value={'kind':'boot','device':args.device,'error':error}
        if instance:value.update(worker_instance=instance,pipeline_epoch=0,token=0)
        emit(value)

    engine=None
    try:
        gst,glib=load_gst()
        if args.probe:
            print(json.dumps({'status':'PASS','version':gst.version_string(),
                              'elements':list(REQUIRED_ELEMENTS),'device_opened':False}))
            return 0
        if args.persistent:
            from tools.gstreamer_persistent_engine import PersistentGstAudioEngine,build_live_pipeline
            if instance:
                from tools.idle_maintenance_engine import IdleMaintenanceEngine
                class Engine(IdleMaintenanceEngine,PersistentGstAudioEngine):pass
                factory=synthetic_pipeline if args.maintenance_fakesink else build_live_pipeline
                engine=Engine.__new__(Engine);engine.configure_idle_maintenance(factory)
                PersistentGstAudioEngine.__init__(engine,gst,args.device,pipeline_factory=factory)
            else:engine=PersistentGstAudioEngine(gst,args.device)
            deadline=time.monotonic()+8
            while not engine.poll()['device_ready']:
                if engine.error or time.monotonic()>=deadline:
                    raise RuntimeError(engine.error or 'Persistent audio warmup timed out')
                time.sleep(.01)
        else:engine=GstAudioEngine(gst,args.device)
    except Exception as exc:
        if engine is not None:engine.release()
        boot(type(exc).__name__+': '+str(exc));return 1

    protocol=None
    if instance:
        from tools.audio_maintenance_wire import WorkerMaintenanceProtocol
        protocol=WorkerMaintenanceProtocol(engine,instance)
    def output(value):emit(protocol.stamp(value) if protocol else value)
    loop=glib.MainLoop();commands=queue.Queue(maxsize=32);eof=threading.Event()

    def receive():
        try:
            for line in sys.stdin:
                if len(line)>8192:eof.set();return
                try:
                    message=json.loads(line)
                    if not isinstance(message,dict):raise ValueError('Expected command object')
                    commands.put(message,timeout=1)
                except (ValueError,queue.Full):eof.set();return
        finally:eof.set()

    def tick():
        try:
            for _ in range(16):
                try:message=commands.get_nowait()
                except queue.Empty:break
                if protocol:
                    accepted,ack=protocol.command(message,commands_pending=not commands.empty())
                    if ack is not None:emit(ack)  # Must precede state for the new epoch.
                else:accepted=engine.command(message)
                if accepted and message.get('type')=='close':loop.quit();return False
            if eof.is_set() and commands.empty():engine.release();loop.quit();return False
            output(dict(engine.poll(),kind='state'))
            if args.echo_reference and hasattr(engine,'take_references'):
                for frame in engine.take_references():
                    output(dict(frame,kind='reference',pcm=base64.b64encode(frame['pcm']).decode('ascii')))
        except (BrokenPipeError,OSError):
            engine.release();loop.quit();return False
        except Exception as exc:
            engine.fail(type(exc).__name__+': '+str(exc))
            output(dict(engine.snapshot(),kind='state'))
        return True

    boot()
    threading.Thread(target=receive,daemon=True,name='aura-gst-commands').start()
    glib.timeout_add(10,tick)
    try:loop.run()
    finally:engine.release()
    return 0


if __name__=='__main__':sys.exit(main())
