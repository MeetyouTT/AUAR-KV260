"""Line-protocol audio worker. EOF/close/stop release only this worker's audio."""
import argparse
import json
from pathlib import Path
import queue
import sys
import threading

AURA = Path(__file__).resolve().parents[1]
if str(AURA) not in sys.path:
    sys.path.insert(0, str(AURA))
from tools.gstreamer_audio_engine import GstAudioEngine, REQUIRED_ELEMENTS


def emit(message):
    print('AUDIO ' + json.dumps(message, ensure_ascii=False), flush=True)


def load_gst():
    import gi
    gi.require_version('Gst', '1.0')
    from gi.repository import Gst, GLib
    Gst.init(None)
    missing = [name for name in REQUIRED_ELEMENTS if Gst.ElementFactory.find(name) is None]
    if missing:
        raise RuntimeError('Missing GStreamer elements: ' + ', '.join(missing))
    return Gst, GLib


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--device', default='hw:CARD=MCP01,DEV=0')
    parser.add_argument('--probe', action='store_true', help='Initialize libraries and list plugins; no device playback')
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
    engine = GstAudioEngine(gst, args.device)
    loop = glib.MainLoop()
    commands = queue.Queue(maxsize=32)
    eof = threading.Event()

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
        try:
            for _ in range(16):
                try:
                    message = commands.get_nowait()
                except queue.Empty:
                    break
                if engine.command(message) and message['type'] == 'close':
                    loop.quit()
                    return False
            if eof.is_set() and commands.empty():
                engine.release()
                loop.quit()
                return False
            emit(dict(engine.poll(), kind='state'))
        except (BrokenPipeError, OSError):
            engine.release()
            loop.quit()
            return False
        except Exception as exc:
            engine.fail(type(exc).__name__ + ': ' + str(exc))
            emit(dict(engine.snapshot(), kind='state'))
        return True

    emit({'kind': 'boot', 'device': args.device, 'error': ''})
    threading.Thread(target=receive, daemon=True, name='aura-gst-commands').start()
    glib.timeout_add(10, tick)
    try:
        loop.run()
    finally:
        engine.release()
    return 0


if __name__ == '__main__':
    sys.exit(main())
