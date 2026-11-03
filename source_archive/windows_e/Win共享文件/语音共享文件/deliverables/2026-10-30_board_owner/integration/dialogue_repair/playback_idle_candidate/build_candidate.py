"""Build only a pinned worker candidate; no audio/GUI/device imports."""
import hashlib
from pathlib import Path

HERE = Path(__file__).resolve().parent
BASE = HERE.parent / 'before/tools/gstreamer_audio_worker.py'
BEFORE_SHA = '63fd37185b6aa6909134945a440be2c33781ed95d2e81dfd95905afe4e17dce7'


def main():
    raw = BASE.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == BEFORE_SHA
    newline = '\r\n' if b'\r\n' in raw else '\n'
    text = raw.decode('utf-8')

    def once(old, new):
        nonlocal text
        old, new = old.replace('\n', newline), new.replace('\n', newline)
        assert text.count(old) == 1
        text = text.replace(old, new, 1)

    once('def main(argv=None):\n', '''def _idle_state_key(engine, state):
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
''')
    once('    eof = threading.Event()\n',
         '    eof = threading.Event()\n    last_idle_key = last_idle_published_at = None\n')
    once('    def tick():\n        try:\n',
         '    def tick():\n        nonlocal last_idle_key, last_idle_published_at\n        command_received = False\n        try:\n')
    once("                if engine.command(message) and message['type'] == 'close':\n",
         "                command_received = True\n                if engine.command(message) and message['type'] == 'close':\n")
    once("            publish(dict(engine.poll(), kind='state', ipc=publisher.snapshot()))\n", '''            state = engine.poll()  # Preserve the original 10ms audio/sink work.
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
''')
    once('        except Exception as exc:\n            engine.fail(type(exc).__name__',
         '        except Exception as exc:\n            last_idle_key = last_idle_published_at = None\n            engine.fail(type(exc).__name__')
    for mode, contents in (('before', raw), ('after', text.encode('utf-8'))):
        path = HERE / mode / 'tools/gstreamer_audio_worker.py'
        path.parent.mkdir(parents=True, exist_ok=True)
        assert not path.exists()
        path.write_bytes(contents)
    print(hashlib.sha256(text.encode('utf-8')).hexdigest())


if __name__ == '__main__':
    main()
