import threading,time
from collections import deque
from types import SimpleNamespace
from unittest.mock import patch
import pytest
from tools import native_grammar as native
from tools.board_recording import RecordingController

def test_incompatible_native_is_deferred_then_revalidated_without_relaxing_checks():
    body={'model':'one'};event=threading.Event()
    with patch.object(native,'_incompatible',{}),patch.object(native.time,'monotonic',return_value=10.) as clock,patch.object(native,'_prepare_verified',side_effect=native.IncompatibleRunner('context')) as prepare:
        with pytest.raises(native.IncompatibleRunner):native.prepare('host',body,4,event)
        with pytest.raises(native.IncompatibleRunner,match='deferred'):native.prepare('host',body,4,event)
        assert prepare.call_count==1
        clock.return_value=41.
        with pytest.raises(native.IncompatibleRunner,match='context'):native.prepare('host',body,4,event)
        assert prepare.call_count==2

@pytest.mark.parametrize('error',[TimeoutError('timed out'),OSError('offline'),InterruptedError('cancelled')])
def test_transient_or_cancel_failure_is_not_cached(error):
    with patch.object(native,'_incompatible',{}),patch.object(native,'_prepare_verified',side_effect=error) as prepare:
        for _ in range(2):
            with pytest.raises(type(error)):native.prepare('host',{'model':'one'},4,threading.Event())
        assert prepare.call_count==2

def test_cancel_still_wins_over_deferred_native():
    event=threading.Event();event.set()
    with patch.object(native,'_incompatible',{('host','one'):(float('inf'),'context')}),patch.object(native,'_prepare_verified') as prepare:
        with pytest.raises(InterruptedError):native.prepare('host',{'model':'one'},4,event)
        prepare.assert_not_called()

def owner_with_events(cost=.002):
    owner=RecordingController.__new__(RecordingController)
    owner.transcription={'request_id':'r','capture_id':'c'}
    owner.requested_at=0
    rows=deque({'context':dict(owner.transcription),'channel_event':{'kind':'audio','index':i},'pcm':bytes([i])} for i in range(64))
    owner.transcriber=SimpleNamespace(feedback_assets={},poll=lambda:rows.popleft() if rows else None)
    seen=[]
    def consume(event,*args):seen.append(event['index']);time.sleep(cost)
    owner.controller=SimpleNamespace(channel_event=consume)
    return owner,rows,seen

def test_pcm_burst_returns_to_render_without_dropping_or_reordering():
    owner,rows,seen=owner_with_events()
    owner._poll_transcription()
    assert 1<=len(seen)<=8 and rows
    while rows:owner._poll_transcription()
    assert seen==list(range(64))

def test_event_count_bound_even_when_processing_is_fast():
    owner,rows,seen=owner_with_events(0)
    owner._poll_transcription()
    assert len(seen)<=8 and len(rows)>=56

def test_status_collect_does_not_drain_pcm():
    owner,rows,seen=owner_with_events()
    owner.capture=None
    RecordingController._collect(owner,poll=False)
    assert len(rows)==64 and seen==[]

