"""A slow renderer must not block preview/touch reads or resurrect cancelled work."""
import threading
import time
import unittest
from PIL import Image

from tools.board_avatar_worker import AvatarRenderWorker


def until(predicate):
    deadline = time.monotonic()+2
    while time.monotonic()<deadline:
        if predicate():return
        time.sleep(.005)
    raise AssertionError('Renderer did not settle')


class Controller:
    def __init__(self, blocked=False):
        self.entered, self.release = threading.Event(), threading.Event()
        if not blocked:self.release.set()
        self.calls = []
        self.last_error = ''
        self.phase = 'IDLE'

    def public(self):return {'phase':self.phase,'error':self.last_error,'log':list(self.calls)}
    def tick(self):
        self.entered.set()
        if not self.release.wait(2):raise RuntimeError('Test renderer was not released')
        return {'image':Image.new('RGBA',(16,16),(200,100,50,255))}
    def submit(self,*args):
        self.calls.append(('submit',threading.get_ident()))
        self.phase = 'VOICE_PREPARING'
        return 'voice-job'
    def cancel(self):
        self.calls.append(('cancel',threading.get_ident()))
        self.phase = 'IDLE'
    def event(self,name):self.cancel()
    def toggle_pause(self):self.calls.append(('pause',threading.get_ident()))


class AvatarWorkerTests(unittest.TestCase):
    def worker(self, blocked=False):
        controller = Controller(blocked)
        worker = AvatarRenderWorker(controller,'#ffffff',(8,8),.02)
        def cleanup():
            controller.release.set()
            worker.close()
        self.addCleanup(cleanup)
        self.assertTrue(controller.entered.wait(1))
        return worker,controller

    def test_reads_and_intents_do_not_wait_for_slow_render(self):
        worker,controller = self.worker(True)
        started = time.monotonic()
        intent = worker.submit('cached line','neutral','')
        packet = worker.read()
        self.assertLess(time.monotonic()-started,.1)
        self.assertEqual(packet['state']['avatar_command_pending'],1)
        self.assertEqual(packet['sequence'],0)
        controller.release.set()
        until(lambda:any(r['command_id']==intent for r in worker.public()['avatar_renderer']['command_results']))
        self.assertEqual(controller.calls[0][1],worker.thread.ident)
        self.assertEqual(worker.public()['phase'],'VOICE_PREPARING')

    def test_cancel_discards_queued_demo_and_previous_generation_frame(self):
        worker,controller = self.worker(True)
        intent = worker.submit('cached line','neutral','')
        worker.cancel()
        self.assertEqual(worker.read()['sequence'],0)
        controller.release.set()
        until(lambda:worker.read()['sequence']>0)
        self.assertFalse(any(c[0]=='submit' for c in controller.calls))
        self.assertEqual(worker.public()['phase'],'IDLE')
        result = next(r for r in worker.public()['avatar_renderer']['command_results'] if r['command_id']==intent)
        self.assertFalse(result['ok'])

    def test_queue_is_bounded_and_cancel_can_preempt_full_queue(self):
        worker,_ = self.worker(True)
        for _ in range(4):worker.toggle_pause()
        with self.assertRaises(ValueError):worker.toggle_pause()
        worker.cancel()
        self.assertEqual(worker.public()['avatar_command_pending'],1)

    def test_expired_intent_does_not_start_audio(self):
        worker,controller = self.worker(True)
        intent = worker.submit('cached line','neutral','')
        with worker.condition:worker.waiting[0]['deadline']=time.monotonic()-1
        controller.release.set()
        until(lambda:any(r['command_id']==intent for r in worker.public()['avatar_renderer']['command_results']))
        self.assertFalse(any(c[0]=='submit' for c in controller.calls))

    def test_latest_frame_and_copied_state_without_frame_queue(self):
        worker,_ = self.worker()
        until(lambda:worker.read()['sequence']>=3)
        packet = worker.read()
        self.assertEqual(len(packet['rgb']),8*8*3)
        self.assertEqual(packet['image'].size,(16,16))
        self.assertTrue(packet['jpeg'].startswith(b'\xff\xd8'))
        packet['state']['log'].append('changed by caller')
        self.assertNotIn('changed by caller',worker.public()['log'])

    def test_close_stops_worker_and_cancels_on_owner_thread(self):
        worker,controller = self.worker()
        worker.close()
        self.assertFalse(worker.thread.is_alive())
        self.assertEqual(controller.calls[-1],('cancel',worker.thread.ident))
        with self.assertRaises(ValueError):worker.toggle_pause()


if __name__=='__main__':unittest.main()
