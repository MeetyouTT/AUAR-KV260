"""Ownership handoff stays ordered and a failed preflight keeps manual control."""
import importlib.util,json,sys,tempfile,threading,time,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]

class Manual:
    def __init__(self,events):self.events=events;self.closed=False
    def read(self):return dict(state='READY',readback=dict(flags=0,lease_left_ms=0),left_sign=1)
    def close(self):self.events.append('manual_close');self.closed=True
    def reverse(self):pass
    def stop(self):return dict(ok=True)
    def jog(self,*a,**kw):return dict(ok=True)


class ProxyTests(unittest.TestCase):
    def setUp(self):
        module=SimpleNamespace(stage_type=lambda base,factory:base)
        with patch.dict(sys.modules,{'tools.pan_controls':module}):
            s=importlib.util.spec_from_file_location('face_proxy',Path(__file__).parent/'face_pan_controls.py')
            self.module=importlib.util.module_from_spec(s);s.loader.exec_module(self.module)
        self.events=[];self.manuals=[]
        def factory():
            self.events.append('manual_create');m=Manual(self.events);self.manuals.append(m);return m
        self.proxy=self.module.FacePanProcess({},manual_factory=factory)
    def tearDown(self):self.proxy.close()
    def test_preflight_failure_does_not_create_a_second_manual_owner(self):
        self.proxy.arguments=lambda:(_ for _ in ()).throw(RuntimeError('changed pin'))
        self.proxy.start();self.proxy.thread.join(1)
        self.assertFalse(self.proxy.running);self.assertFalse(self.manuals[0].closed)
        self.assertEqual(self.events,['manual_create'])
    def test_manual_closes_before_follow_and_reopens_after_child_exit(self):
        events=self.events
        with tempfile.TemporaryDirectory() as tmp:
            out=Path(tmp)/'result.json';self.proxy.arguments=lambda:(['finite'],out)
            class Child:
                returncode=0
                def __init__(child,*args,**kwargs):
                    self.assertTrue(self.manuals[0].closed);events.append('follow_open')
                def communicate(child,timeout):
                    events.append('follow_exit');out.write_text(json.dumps(dict(status='STOPPED',result=dict(reason='TIME_LIMIT',stopped=dict(flags=0)))))
                    return '',''
                def poll(child):return 0
            with patch.object(self.module.subprocess,'Popen',Child):
                self.proxy.start();self.proxy.thread.join(1)
            self.assertEqual(self.events,['manual_create','manual_close','follow_open','follow_exit','manual_create'])
            self.assertEqual(self.proxy.result['final_flags'],0)
    def test_jog_is_refused_during_follow(self):
        self.proxy.running=True
        with self.assertRaises(ValueError):self.proxy.jog('left')
        self.proxy.running=False

    def test_explicit_follow_lock_keeps_manual_owner_and_creates_no_child(self):
        self.proxy.config['automatic_following_enabled']=False
        with patch.object(self.module.subprocess,'Popen') as child:
            with self.assertRaisesRegex(ValueError,'尚未开放'):self.proxy.start()
            child.assert_not_called()
        self.assertFalse(self.proxy.running)
        self.assertIsNone(self.proxy.thread)
        self.assertFalse(self.manuals[0].closed)
        self.assertEqual(self.events,['manual_create'])
        self.assertTrue(self.proxy.jog('left')['ok'])

    def test_invalid_follow_permission_is_refused(self):
        for value in [0,1,'true',None]:
            self.proxy.config['automatic_following_enabled']=value
            with self.assertRaises(ValueError):self.proxy.start()
        self.assertEqual(self.events,['manual_create'])

    def test_explicit_permission_retains_preflight_and_owner_checks(self):
        self.proxy.config['automatic_following_enabled']=True
        self.proxy.arguments=lambda:(_ for _ in ()).throw(RuntimeError('changed pin'))
        self.proxy.start();self.proxy.thread.join(1)
        self.assertFalse(self.proxy.running)
        self.assertFalse(self.manuals[0].closed)
        self.assertEqual(self.events,['manual_create'])


if __name__=='__main__':unittest.main()
