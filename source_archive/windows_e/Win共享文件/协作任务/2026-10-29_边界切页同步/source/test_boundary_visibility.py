import json,queue,socket,tempfile,threading,time,types,unittest
from pathlib import Path
from unittest.mock import patch
from boundary_visibility import PageGate,VisibilityClient,VisibilityServer
from test_zone_editor_v5 import load_editor,Thread

def message(page,sequence,pid=10,birth=20,boot='test'):
    return dict(version=1,boot=boot,pid=pid,birth=birth,sequence=sequence,page=page,request=str(sequence))

class VisibilityTests(unittest.TestCase):
    def test_late_vision_update_cannot_reopen_after_hidden_page(self):
        gate=PageGate('test');gate.accept(message('vision',1));gate.accept(message('main',2))
        self.assertFalse(gate.allows_overlay());self.assertIsNone(gate.accept(message('vision',1)))
        self.assertFalse(gate.allows_overlay())

    def test_new_gui_rejects_old_gui_and_wrong_boot(self):
        gate=PageGate('test');gate.accept(message('main',2));gate.accept(message('vision',1,pid=11,birth=30))
        self.assertIsNone(gate.accept(message('main',99)));self.assertTrue(gate.allows_overlay())
        self.assertIsNone(gate.accept(message('main',3,pid=11,birth=30,boot='old')))
        for value in [None,[],True,{},'vision']:self.assertIsNone(gate.accept(value))

    def test_hide_ack_waits_for_application_callback(self):
        with tempfile.TemporaryDirectory() as td:
            pending=queue.Queue();events=[]
            server=VisibilityServer(lambda fn,*args:pending.put((fn,args)),lambda page:events.append(('unmapped',page)),address=td+'/page.sock',boot='test')
            try:
                client=VisibilityClient(td+'/page.sock',None,{'boot':'test','pid':10,'birth':20},timeout=.5);answers=[]
                worker=threading.Thread(target=lambda:answers.append(client.send('main')));worker.start()
                fn,args=pending.get(timeout=.3);self.assertFalse(answers);self.assertTrue(worker.is_alive())
                fn(*args);worker.join(.3)
                self.assertTrue(answers[0]['acknowledged']);self.assertEqual(events,[('unmapped','main')])
            finally:server.close()

    def test_fast_round_trip_and_stale_callbacks(self):
        with tempfile.TemporaryDirectory() as td:
            pending=queue.Queue();applied=[]
            server=VisibilityServer(lambda fn,*a:pending.put((fn,a)),applied.append,address=td+'/page.sock',boot='test')
            try:
                client=VisibilityClient(td+'/page.sock',None,{'boot':'test','pid':10,'birth':20})
                client.send('vision',False);first=pending.get(timeout=.3)
                client.send('main',False);second=pending.get(timeout=.3)
                first[0](*first[1]);second[0](*second[1]);self.assertEqual(applied,['main'])
                client.send('vision',False);fn,args=pending.get(timeout=.3);fn(*args)
                self.assertEqual(applied,['main','vision']);self.assertTrue(server.gate.allows_overlay())
            finally:server.close()

    def test_missing_server_does_not_block_navigation(self):
        with tempfile.TemporaryDirectory() as td:
            c=VisibilityClient(td+'/missing.sock',None,{'boot':'test','pid':10,'birth':20})
            started=time.monotonic();self.assertFalse(c.send('main')['acknowledged']);self.assertLess(time.monotonic()-started,.15)

    def test_editor_hides_all_overlays_and_suppresses_old_poll(self):
        module=load_editor()
        with tempfile.TemporaryDirectory() as td:
            with patch.object(module.threading,'Thread',Thread):editor=module.Editor(Path(td)/'settings.json')
            gate=PageGate('test');editor.visibility_channel=types.SimpleNamespace(gate=gate)
            gate.accept(message('vision',1));editor.update(True,[100,100,100,100])
            self.assertTrue(editor.line.visible);self.assertTrue(any(p.visible for p in editor.faces))
            gate.accept(message('main',2));editor.update(True,[100,100,100,100])
            windows=[editor.line,editor.left_line,editor.center_line,editor.hint_window,editor.panel]+editor.faces
            self.assertTrue(all(not w.visible for w in windows))
            gate.accept(message('vision',3));editor.update(True,None)
            self.assertTrue(editor.line.visible);self.assertTrue(editor.left_line.visible)

    def test_page_hide_cancels_drag_and_syncs_after_unmapping(self):
        module=load_editor()
        with tempfile.TemporaryDirectory() as td:
            with patch.object(module.threading,'Thread',Thread):editor=module.Editor(Path(td)/'settings.json')
            editor.update(True,None);editor.drag=True;events=[]
            def sync():
                self.assertFalse(editor.line.visible);self.assertFalse(editor.left_line.visible);events.append('synced')
            module.Gdk.Display=types.SimpleNamespace(get_default=lambda:types.SimpleNamespace(sync=sync))
            editor.page_visibility_applied('main')
            self.assertFalse(editor.drag);self.assertEqual(events,['synced']);self.assertTrue(editor.poll_wakeup.is_set())

if __name__=='__main__':unittest.main()
