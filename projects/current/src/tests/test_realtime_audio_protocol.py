"""Canceled generations cannot return through the audio-process status channel."""
import json
import threading
from types import SimpleNamespace
from tools.realtime_audio import SelectedAudioOutput

def facade(lines=()):
    output=object.__new__(SelectedAudioOutput);output.active=True;output.paused=False;output.duration=2.;output.last_time=0.;output.token=4;output.closed=True
    output.lock=threading.Lock();output.snapshot={'ready':False,'clock':0.,'done':False,'error':''};output.booted=threading.Event()
    output.process=SimpleNamespace(stdout=['AUDIO '+json.dumps(row)+'\n' for row in lines],poll=lambda:0)
    return output

def test_stale_ready_and_eof_messages_cannot_replace_current_clock():
    output=facade([{'kind':'boot','device':'test speaker'},
                   {'token':3,'ready':True,'clock':1.8,'done':True},
                   {'token':4,'ready':True,'clock':.4},
                   {'token':3,'clock':2.,'done':True}])
    output.receive();assert output.booted.is_set() and output.device_description=='test speaker'
    assert output.ready and output.position()==.4 and not output.read()['done']

def test_dead_audio_process_still_allows_local_stop_and_generation_invalidation():
    output=facade();output.stop()
    assert not output.active and output.token==5 and output.position()==0
