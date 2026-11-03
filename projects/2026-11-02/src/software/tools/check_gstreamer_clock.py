"""Native conversion/clock check using fakesink; never opens an audio device."""
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import time
import wave

AURA = Path(__file__).resolve().parents[1]
if str(AURA) not in sys.path:
    sys.path.insert(0, str(AURA))
from tools.gstreamer_audio_engine import GstAudioEngine, build_pipeline
from tools.gstreamer_audio_worker import load_gst


def main():
    gst, unused = load_gst()
    observed = {'caps': [], 'bytes': 0}

    def build_without_device(gst, path, device):
        pipeline, unopened_sink = build_pipeline(gst, path, device)
        caps = pipeline.get_by_name('capsfilter')
        caps.unlink(unopened_sink)
        pipeline.remove(unopened_sink)
        sink = gst.ElementFactory.make('fakesink', 'no-audio-device')
        if sink is None:
            raise RuntimeError('fakesink unavailable')
        sink.set_property('sync', True)
        pipeline.add(sink)
        if not caps.link(sink):
            raise RuntimeError('Cannot link native clock probe')

        def output_buffer(pad, info):
            current = pad.get_current_caps().get_structure(0)
            record = {key: current.get_value(key) for key in ('format', 'rate', 'channels')}
            if record not in observed['caps']:
                observed['caps'].append(record)
            observed['bytes'] += info.get_buffer().get_size()
            return gst.PadProbeReturn.OK

        caps.get_static_pad('src').add_probe(gst.PadProbeType.BUFFER, output_buffer)
        return pipeline, sink

    engine = GstAudioEngine(gst, 'NO_DEVICE_IN_NATIVE_TEST', pipeline_factory=build_without_device)

    def until(predicate, limit=3):
        deadline = time.monotonic()+limit
        while time.monotonic() < deadline:
            state = engine.poll()
            if state['error']:
                raise RuntimeError(state['error'])
            if predicate(state):
                return state
            time.sleep(.004)
        raise RuntimeError('Native GStreamer condition timed out')

    try:
        with tempfile.TemporaryDirectory(prefix='aura-gst-clock-') as temp:
            path = Path(temp)/'fixture.wav'
            with wave.open(str(path), 'wb') as stream:
                stream.setnchannels(1)
                stream.setsampwidth(2)
                stream.setframerate(24000)
                stream.writeframes(b'\x01\x00'*24000)
            sha = hashlib.sha256(path.read_bytes()).hexdigest()
            engine.command({'type':'play','token':1,'path':str(path),'sha256':sha})
            until(lambda state:state['ready'] and state['clock']>=.12)
            engine.command({'type':'pause','token':1,'paused':True})
            result, actual_state, pending = engine.pipeline.get_state(gst.SECOND)
            assert actual_state == gst.State.PAUSED
            paused = engine.poll()['clock']
            ok, before = engine.sink.query_position(gst.Format.TIME)
            assert ok
            time.sleep(.12)
            assert engine.poll()['clock'] == paused
            ok, after = engine.sink.query_position(gst.Format.TIME)
            assert ok and abs(after-before) <= 25000000
            engine.command({'type':'pause','token':1,'paused':False})
            until(lambda state:state['clock']>paused+.04)
            old_pipeline = engine.pipeline
            engine.command({'type':'stop','token':2})
            assert engine.pipeline is None and not engine.poll()['ready']
            assert old_pipeline.get_state(gst.SECOND)[1] == gst.State.NULL
            assert not engine.command({'type':'play','token':1,'path':str(path),'sha256':sha})
            observed['bytes'] = 0
            observed['caps'].clear()
            engine.command({'type':'play','token':3,'path':str(path),'sha256':sha})
            final = until(lambda state:state['done'])
            assert final['clock'] == 1.0
            assert observed['caps'] == [{'format':'S16LE','rate':48000,'channels':2}]
            assert abs(observed['bytes']-48000*2*2) <= 8
        print(json.dumps({'status':'PASS','gstreamer':gst.version_string(),
            'pause_freezes_sink_position':True,'resume_advances_position':True,'cancel_releases_pipeline':True,
            'old_generation_rejected':True,'eos_settles_duration':True,'converted_caps':observed['caps'],
            'converted_bytes':observed['bytes'],'device_opened':False,
            'scope':'NATIVE_GSTREAMER_FAKESINK_TEST_NOT_MCP01_OR_AVATAR_ACCEPTANCE'}))
        return 0
    finally:
        engine.release()


if __name__ == '__main__':
    sys.exit(main())
