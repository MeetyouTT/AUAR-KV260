"""A slow UI snapshot must not hold already received native pixels."""
import threading,time
import queue
from types import SimpleNamespace
from tools.board_avatar_worker import AvatarRenderWorker

def test_remote_handoff_precedes_blocking_public_snapshot():
    entered=threading.Event();release=threading.Event();presented=threading.Event()
    class Controller:
        phase='SPEAKING';last_error=''
        def __init__(self):
            self.seq=0;self.public_calls=0
            self.core=SimpleNamespace(talk_gen=1,fsm=SimpleNamespace(state=SimpleNamespace(label='SPEAKING')))
            self.portrait_offload=SimpleNamespace(target_fps=16,session='test',status=lambda:{'mode':'remote'},close=lambda:None)
        def tick(self):
            self.seq+=1
            return {'_portrait_rgb':b'\x11\x22\x33'*64,'_portrait_sequence':self.seq,'_portrait_expires':time.monotonic()+.15}
        def public(self):
            self.public_calls+=1
            if self.public_calls==2:
                entered.set()
                if not release.wait(2):raise RuntimeError('Test snapshot timed out')
            return {'phase':self.phase,'error':self.last_error}
        def cancel(self):pass
    c=Controller()
    worker=AvatarRenderWorker(c,'white',(8,8),1/24,native_video=SimpleNamespace(push=lambda *a:presented.set()),visual_fps=16)
    try:
        assert entered.wait(2)
        assert presented.wait(.5),'Native handoff was blocked by UI snapshot'
        assert not c.last_error
    finally:
        release.set();worker.close()

def test_performance_separates_remote_and_fallback_budgets():
    from tools.render_performance import PerformanceRecorder
    r=PerformanceRecorder.__new__(PerformanceRecorder)
    r.period=5;r.start=None;r.previous=None;r.groups={};r.last_sequence=None
    r.queue=queue.Queue();r.dropped=0
    r.observe('SPEAKING','SPEAKING',0,1,{'target_fps':16})
    r.observe('SPEAKING','SPEAKING',.1,2,{'target_fps':16})
    r.observe('SPEAKING','SPEAKING',.2,3,{'target_fps':8})
    r.observe('SPEAKING','SPEAKING',.325,4,{'target_fps':8})
    r.flush(.4);row=r.queue.get_nowait()
    assert row['target_fps'] is None
    fast,local=row['phases']
    assert fast['target_fps']==16 and fast['long_frame_budget_ms']==93.75 and fast['over_budget']==1
    assert local['target_fps']==8 and local['interval_ms']['count']==1 and local['over_budget']==0

