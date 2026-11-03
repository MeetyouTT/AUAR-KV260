"""Real owned child-process fault injection; no model, audio device or network."""
import io
import json
import os
from pathlib import Path
import sys
import threading
import time
from types import SimpleNamespace

import pytest

from common.voice_channel import read_frame
from tools.voice_channel_source import channel_frames
from tools.voice_worker_transport import BoundedSpeechProcess


CHILD = r'''
import json,sys,time
for line in sys.stdin:
    request=json.loads(line);kind=request.get('text','ok');token=request['request_id']
    if kind=='hang':time.sleep(30)
    if kind=='partial':sys.stdout.write('RESULT {');sys.stdout.flush();time.sleep(30)
    if kind=='exit':sys.exit(3)
    if kind=='mismatch':token='obsolete-request'
    if kind=='slow':time.sleep(.5)
    print('RESULT '+json.dumps({'request_id':token,'ok':True,'result':{'echo':kind}}),flush=True)
'''


@pytest.fixture
def worker(tmp_path):
    script=tmp_path/'fake_speech_worker.py'
    script.write_text(CHILD,encoding='utf-8')
    transport=BoundedSpeechProcess(lambda:[sys.executable,'-B','-u',str(script)],tmp_path/'fake_worker.log')
    yield transport
    transport.close()


@pytest.mark.parametrize('kind',['hang','partial'])
def test_hang_or_partial_line_releases_owner_and_next_request_recovers(worker,kind):
    start=time.monotonic()
    with pytest.raises(TimeoutError):worker.request({'text':kind},timeout=.3,request_id='failed')
    failed=worker.process
    assert time.monotonic()-start<2
    assert failed.poll() is not None
    assert not worker.lock.locked()
    assert worker.request({'text':'ok'},timeout=2,request_id='next')=={'echo':'ok'}
    assert worker.process is not failed
    assert worker.health()['alive'] and not worker.health()['quarantined']


@pytest.mark.parametrize('kind,match',[('exit','worker'),('mismatch','another request')])
def test_exited_or_wrong_generation_worker_is_not_reused(worker,kind,match):
    with pytest.raises(RuntimeError,match=match):worker.request({'text':kind},timeout=2,request_id='expected')
    failed=worker.process
    assert failed.poll() is not None
    assert worker.request({'text':'ok'},timeout=2)=={'echo':'ok'}
    assert worker.process is not failed


def test_waiting_request_timeout_does_not_terminate_another_owner(worker):
    errors=[]
    def first():
        try:worker.request({'text':'hang'},timeout=3,request_id='first')
        except Exception as exc:errors.append(exc)
    thread=threading.Thread(target=first)
    thread.start()
    try:
        until=time.monotonic()+2
        while worker.active_id!='first' and time.monotonic()<until:time.sleep(.01)
        assert worker.active_id=='first'
        owned=worker.process
        assert not worker.cancel_request('stale-id')
        with pytest.raises(TimeoutError):worker.request({'text':'ok'},timeout=.1,request_id='second')
        assert owned.poll() is None
        assert worker.cancel_request('first')
    finally:
        worker.close();thread.join(2)
    assert not thread.is_alive() and errors


def test_cancellation_event_stops_partial_line_without_waiting_for_newline(worker):
    cancelled=threading.Event()
    timer=threading.Timer(.2,cancelled.set);timer.start()
    started=time.monotonic()
    try:
        with pytest.raises(InterruptedError):worker.request({'text':'partial'},timeout=5,cancelled=cancelled)
    finally:timer.cancel()
    assert time.monotonic()-started<2
    assert worker.process.poll() is not None


def test_channel_deadline_releases_outer_model_lock_and_owns_tts_cleanup(worker):
    class Voice:
        def generate_bounded(self,text,**kwargs):
            return worker.request({'text':'partial'},**kwargs)
        def cancel_request(self,request_id):return worker.cancel_request(request_id)
    class Stream:
        def __iter__(self):
            yield 'text','合成故障测试。'
            yield 'speech_ready',None
            yield 'complete',{'reply_text':'合成故障测试。','emotion':'friendly','avatar_action':''}
        def cancel(self):pass
    from tests.framework.test_voice_channel import owner
    models=SimpleNamespace(histories={},voice=Voice(),latency_options={},lock=threading.Lock())
    kinds=[]
    started=time.monotonic()
    with models.lock:
        for packet in channel_frames(models,owner(),'合成测试',.3,model='fake',host='fake',
                                     stream_factory=lambda *a,**kw:Stream()):
            header,_=read_frame(io.BytesIO(packet));kinds.append(header['kind'])
    assert time.monotonic()-started<2
    assert 'error' in kinds
    assert not models.lock.locked()
    assert worker.process.poll() is not None
    assert worker.request({'text':'ok'},timeout=2)=={'echo':'ok'}


def test_close_prevents_restarting_a_worker(worker):
    worker.request({'text':'ok'},timeout=2)
    process=worker.process
    worker.close()
    assert process.poll() is not None
    with pytest.raises(RuntimeError,match='closed'):worker.request({'text':'ok'},timeout=2)


def test_child_not_reading_stdin_cannot_hold_request_past_deadline(tmp_path):
    script=tmp_path/'not_reading.py'
    script.write_text('import time; time.sleep(30)',encoding='utf-8')
    child=BoundedSpeechProcess(lambda:[sys.executable,'-B','-u',str(script)],tmp_path/'no_read.log')
    started=time.monotonic()
    try:
        with pytest.raises(TimeoutError):child.request({'text':'x'*7800},timeout=.3)
        assert time.monotonic()-started<2
        assert not child.lock.locked()
        assert child.process.poll() is not None
        assert not child.writer.is_alive()
    finally:child.close()


def test_cancel_rechecks_request_after_owner_changes(worker,monkeypatch):
    worker.request({'text':'ok'},timeout=2)
    worker.active_id='old'
    retire=worker._retire
    def changed_owner(process,reason,**kwargs):
        worker.active_id='new'
        return retire(process,reason,**kwargs)
    monkeypatch.setattr(worker,'_retire',changed_owner)
    assert not worker.cancel_request('old')
    assert worker.process.poll() is None
    worker.active_id=None


@pytest.mark.skipif(os.name!='nt',reason='Windows parent-lifetime ownership')
def test_closing_owned_job_terminates_its_exact_speech_child(worker):
    worker.request({'text':'ok'},timeout=2)
    child=worker.process
    assert worker.job.handle
    worker.job.close()
    child.wait(timeout=2)
    assert child.poll() is not None
    assert worker.request({'text':'ok'},timeout=2)=={'echo':'ok'}
