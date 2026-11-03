"""Fast fake-backend lifecycle checks; no sockets/GPU/services/databases."""
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import threading
import types
import unittest
from unittest.mock import patch

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
import production_runtime as runtime


class ControlTests(unittest.TestCase):
    def test_control_is_session_and_action_bound(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'CONTROL.json'
            value=dict(session_id='a'*32,control_id='b'*32,action='stop')
            path.write_text(json.dumps(value))
            self.assertEqual(runtime.control(path,'a'*32),value)
            with self.assertRaises(ValueError):runtime.control(path,'c'*32)
            value['action']='kill';path.write_text(json.dumps(value))
            with self.assertRaises(ValueError):runtime.control(path,'a'*32)

    def test_error_never_includes_exception_text(self):
        self.assertEqual(runtime.safe_error(ValueError('PRIVATE_INPUT_MUST_NOT_APPEAR')),
            dict(error_type='ValueError',error_code='model_owner_operation_failed'))

    def test_owned_release_refuses_changed_daemon(self):
        state=dict(owns_fixed_model=True,fixed_daemon_owner=dict(pid=1))
        fake=types.ModuleType('project_ollama');fake.inspect_ownership=lambda:dict(pid=2)
        with patch.dict(sys.modules,{'project_ollama':fake}),patch.object(runtime,'ollama_json') as http:
            with self.assertRaises(RuntimeError):runtime.require_owned_model(state)
            http.assert_not_called()

    def test_owned_release_refuses_other_model(self):
        owner=dict(pid=1,creation_utc='source',executable='ollama',command_line='serve',listeners=[])
        fake=types.ModuleType('project_ollama');fake.inspect_ownership=lambda:owner
        with patch.dict(sys.modules,{'project_ollama':fake}),patch.object(runtime,'ollama_json',return_value={'models':[{'name':'foreign-model'}]}):
            with self.assertRaises(RuntimeError):runtime.require_owned_model(dict(owns_fixed_model=True,fixed_daemon_owner=owner))


class LifecycleTests(unittest.TestCase):
    def lifecycle(self,action='stop',startup_failure=False):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);session='d'*32;events=[];held=[]
            from tools.service_instance_lock import ServiceInstanceLock
            class Lock(ServiceInstanceLock):
                def acquire(self):
                    super().acquire();held.append(self);return self
            class Voice:
                process=types.SimpleNamespace(pid=123)
                closed=False
                def health(self):return {'alive':not self.closed}
            class Backend:
                voice=Voice()
                @classmethod
                def from_config(cls,**kwargs):return cls()
                def close(self):
                    self_check=held[0].held
                    if not self_check:raise AssertionError('lifetime lock released before TTS close')
                    self.voice.closed=True;events.append('tts_closed_under_lock')
            class Host:
                def __init__(self,backend):
                    self.backend=backend;self.condition=threading.RLock();self.closed=False
                    self.active=None;self.pending=[];self.jobs={}
                def close(self):self.closed=True;self.backend.close()
            class Server:
                def __init__(self):self.event=threading.Event()
                def serve_forever(self,**kwargs):self.event.wait(2.)
                def shutdown(self):self.event.set();events.append('server_closed')
                def server_close(self):pass
            def startup(*args,**kwargs):
                if startup_failure:raise RuntimeError('sensitive_exception_not_logged')
                return dict(ready=True)
            module_host=types.ModuleType('tools.model_inference_host')
            module_host.LocalModelBackend=Backend;module_host.InferenceHost=Host
            module_host.make_server=lambda *a,**k:Server()
            module_start=types.ModuleType('tools.model_inference_startup');module_start.startup_models=startup
            module_guard=types.ModuleType('tools.voice_startup_guard')
            module_guard.cold_capacity_preflight=lambda *a,**k:dict(extra={'project_model_resident':False})
            module_ollama=types.ModuleType('project_ollama')
            module_ollama.ensure=lambda:dict(ready=True,ownership=dict(pid=12))
            original_write=runtime.write_json
            def write(path,value):
                original_write(path,value)
                if value.get('status')=='READY':
                    original_write(root/'sessions'/session/'CONTROL.json',
                        dict(session_id=session,control_id='e'*32,action=action))
            def release(state):
                self.assertTrue(held[0].held);self.assertIn('tts_closed_under_lock',events)
                events.append('own_model_released');return dict(released=True)
            before_out,before_err=sys.stdout,sys.stderr
            try:
                with patch.object(runtime,'HERE',root),patch.object(runtime,'RUNTIME',root/'lifetime'),\
                    patch.object(runtime,'config',return_value=(dict(host='192.168.50.1',port=8797,allowed_peers=['192.168.50.2'],local_health=True,voice_python=sys.executable),'f'*64)),\
                    patch.object(runtime,'write_json',side_effect=write),patch.object(runtime,'require_owned_model',return_value=True),\
                    patch.object(runtime,'release_owned_model',side_effect=release),\
                    patch('tools.service_instance_lock.ServiceInstanceLock',Lock),\
                    patch.dict(sys.modules,{'tools.model_inference_host':module_host,'tools.model_inference_startup':module_start,
                        'tools.voice_startup_guard':module_guard,'project_ollama':module_ollama}):
                    code=runtime.main(['--session-id',session])
            finally:
                sys.stdout.close();sys.stderr.close();sys.stdout,sys.stderr=before_out,before_err
            state=json.loads((root/'sessions'/session/'status.json').read_bytes())
            self.assertFalse(held[0].held)
            self.assertIn('tts_closed_under_lock',events)
            return state,events,code

    def test_no_ttl_default_stop_keeps_model(self):
        state,events,code=self.lifecycle()
        self.assertEqual(code,0);self.assertEqual(state['status'],'CLOSED')
        self.assertIsNone(state['lifetime_seconds']);self.assertNotIn('own_model_released',events)

    def test_explicit_release_after_tts_close_under_same_lock(self):
        state,events,code=self.lifecycle('release_owned_model')
        self.assertEqual(code,0);self.assertTrue(state['model_release']['released'])
        self.assertLess(events.index('tts_closed_under_lock'),events.index('own_model_released'))

    def test_startup_failure_closes_owned_tts_before_unlock(self):
        state,events,code=self.lifecycle(startup_failure=True)
        self.assertEqual(code,1);self.assertEqual(state['status'],'FAILED')
        self.assertNotIn('sensitive_exception',json.dumps(state))


if __name__=='__main__':unittest.main()
