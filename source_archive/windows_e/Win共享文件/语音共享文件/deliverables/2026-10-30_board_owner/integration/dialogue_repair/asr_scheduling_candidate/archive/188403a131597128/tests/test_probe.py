"""Fake priority/task scope and slot contracts only; no actual model or device."""
import ast
from contextlib import ExitStack
import importlib.util
import io
import json
from pathlib import Path
import sys
import tempfile
from types import ModuleType, SimpleNamespace
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('scheduling_probe', HERE/'probe_asr_scheduling.py')
probe = importlib.util.module_from_spec(spec); spec.loader.exec_module(probe)
PIPELINE = HERE.parents[1]/'resume_frontend_optimization/board_audio_runtime_probe.py'
pipeline = probe.load('_actual_reviewed_priority', PIPELINE, probe.PIPELINE_SHA)


class Api:
    PRIO_PROCESS = 0
    def __init__(self):
        self.owned = {101, 102}; self.values = {101:0, 102:0, 999:7}; self.writes = []
    def getpid(self): return 101
    def getpriority(self, which, tid): return self.values[tid]
    def setpriority(self, which, tid, value):
        if tid not in self.owned: raise AssertionError('external task mutation')
        self.writes.append((tid,value)); self.values[tid] = value
    def priority(self, nice):
        return pipeline.ProbeProcessPriority(nice, api=self, thread_ids=lambda:list(self.owned))


class Tests(unittest.TestCase):
    def test_only_zero_or_minus_five_and_fixed_three_threads(self):
        seen = []
        fake = SimpleNamespace(ProbeProcessPriority=lambda x:seen.append(x))
        for value in (0,-5): probe.priority_lease(fake,value)
        for value in (True,False,-10,-20,1,0.,None,'-5'):
            with self.subTest(value=value), self.assertRaises(probe.Refused): probe.priority_lease(fake,value)
        self.assertEqual(seen,[0,-5])
        self.assertEqual(probe.ORDER,(0,-5,-5,0))
        self.assertEqual(probe.model_arguments('/public/model')['num_threads'],3)

    def test_reviewed_helper_restores_owned_existing_and_new_threads_on_error(self):
        api = Api(); lease = api.priority(-5)
        with self.assertRaisesRegex(RuntimeError,'synthetic'):
            with lease:
                self.assertEqual([api.values[t] for t in api.owned],[-5,-5])
                api.owned.add(103); api.values[103] = -5
                raise RuntimeError('synthetic')
        self.assertTrue(lease.record['restoration_confirmed'])
        self.assertEqual({api.values[t] for t in api.owned},{0})
        self.assertEqual(api.values[999],7)
        self.assertFalse(any(t==999 for t,_ in api.writes))

    def test_reviewed_helper_refuses_permission_and_restores_partial_change(self):
        api = Api(); original = api.setpriority
        def setpriority(which,tid,value):
            if tid==102 and value==-5: raise PermissionError()
            return original(which,tid,value)
        api.setpriority = setpriority
        lease = api.priority(-5)
        with self.assertRaises(pipeline.ProbePriorityError):
            with lease: self.fail('must not enter')
        self.assertTrue(lease.record['restoration_confirmed'])
        self.assertEqual(api.values[101],0)

    def test_kill_requires_matching_birth_own_group_and_non_parent(self):
        calls = []
        proc = SimpleNamespace(pid=321,poll=lambda:None)
        api = SimpleNamespace(getpid=lambda:100,getpgrp=lambda:100,getpgid=lambda p:321,
                              killpg=lambda p,s:calls.append((p,s)))
        guard = SimpleNamespace(proc=lambda p:dict(birth=123))
        with patch.object(probe,'os',api), patch.object(probe,'signal',SimpleNamespace(SIGKILL=9)):
            probe.kill_owned(proc,123,guard)
            with self.assertRaises(probe.Refused): probe.kill_owned(proc,999,guard)
            api.getpgid = lambda p:100
            with self.assertRaises(probe.Refused): probe.kill_owned(proc,123,guard)
        self.assertEqual(calls,[(321,9)])

    def test_numeric_counters_use_only_verified_public_fields(self):
        gui = dict(avatar_display=dict(frames=7,target_fps=16,paint_at=10.,secret_name='hidden'),reply='private ignored')
        camera = dict(capture_frames=9,detected_frames=8,observation_age_ms=90,people=['hidden'])
        guard = SimpleNamespace(get=lambda h,p,path:gui if p==8783 else camera)
        result = probe.numeric_context(guard,SimpleNamespace(camera_health_port=8790))
        self.assertTrue(result['gui_numeric_available']); self.assertTrue(result['camera_numeric_available'])
        self.assertEqual(set(result['gui']),{'avatar_display.frames','avatar_display.target_fps','avatar_display.paint_at'})
        self.assertEqual(result['camera'],dict(capture_frames=9,detected_frames=8,observation_age_ms=90))
        self.assertNotIn('hidden',json.dumps(result)); self.assertNotIn('private',json.dumps(result))

    def fake_slot(self, fail=False):
        api = Api(); events = []; calls = []; lease_box = []
        class Model:
            def __init__(self,**kwargs):
                events.append(('model_load',api.values[101])); self.kwargs=kwargs
                api.owned.add(103); api.values[103]=0
                self.calls=0; calls.append(kwargs)
            def transcribe(self,pcm,*,deadline):
                self.calls+=1; events.append(('decode',api.values[101]))
                if self.calls==1: api.owned.add(104); api.values[104]=api.values[101]
                if fail and self.calls==2: raise RuntimeError('synthetic decode failure')
                return '公开合成结果'
        class Wave:
            def __enter__(self): return self
            def __exit__(self,*a): pass
            def getnchannels(self): return 1
            def getsampwidth(self): return 2
            def getframerate(self): return 16000
            def getnframes(self): return 1600
            def readframes(self,n): return b'\x01\0'*n
        def metadata(*a,**kw):
            self.assertEqual(api.values[101],0)
            events.append(('guard',api.values[101]))
            return dict(ui=dict(pid=2),camera=dict(pid=3),memory=dict(completed=4),model_idle=True)
        guard = SimpleNamespace(metadata=metadata,available_mib=lambda:4096,
                                get=lambda *a:dict(avatar_display=dict(frames=1)))
        def priority(nice):
            lease=api.priority(nice);lease_box.append(lease);return lease
        asr = ModuleType('board.runtime.audio.board_asr');asr.BoardParaformer=Model
        resource = SimpleNamespace(RUSAGE_SELF=0,getrusage=lambda _:SimpleNamespace(ru_maxrss=1024))
        modules={'board.runtime.audio.board_asr':asr,'resource':resource}
        for name in ('board','board.runtime','board.runtime.audio'):
            modules[name]=ModuleType(name);modules[name].__path__=[]
        with tempfile.TemporaryDirectory(prefix='public-scheduling-') as directory, ExitStack() as stack:
            root=Path(directory);config=root/'runtime/aura/config/board_avatar_gtk.json'
            config.parent.mkdir(parents=True);config.write_text(json.dumps(dict(board_business=dict(asr_directory='/public/fake'))))
            args=SimpleNamespace(runtime_root=str(root),pipeline_source='/public/pipeline',slot_nice=-5,
                                 min_available_mib=1500,camera_health_port=None)
            stack.enter_context(patch.dict(sys.modules,modules))
            stack.enter_context(patch.object(probe,'load',return_value=SimpleNamespace(ProbeProcessPriority=priority)))
            stack.enter_context(patch.object(probe,'sha',side_effect=lambda p:probe.ASR_SHA if Path(p).name=='board_asr.py' else probe.WAV_SHA))
            stack.enter_context(patch.object(probe.wave,'open',return_value=Wave()))
            if fail:
                with self.assertRaisesRegex(RuntimeError,'synthetic decode'): probe.slot(args,guard)
                result=None
            else: result=probe.slot(args,guard)
        return api,events,calls,lease_box,result

    def test_actual_slot_loads_at_zero_and_times_decode_at_minus_five_then_restores(self):
        api,events,calls,leases,result=self.fake_slot()
        self.assertIn(('model_load',0),events)
        self.assertEqual([v for k,v in events if k=='decode'],[-5,-5])
        self.assertEqual(calls[0]['num_threads'],3)
        self.assertTrue(result['priority']['restoration_confirmed'])
        self.assertEqual({api.values[t] for t in api.owned},{0})
        self.assertTrue(result['same_as_warmup'])

    def test_actual_slot_exception_still_restores_new_ort_tasks(self):
        api,events,calls,leases,result=self.fake_slot(fail=True)
        self.assertTrue(leases[0].record['restoration_confirmed'])
        self.assertEqual({api.values[t] for t in api.owned},{0})

    def test_fixed_error_codes_and_python39(self):
        self.assertEqual(probe.failure_code(RuntimeError('sensitive body')), 'probe_runtime_error')
        self.assertEqual(probe.failure_code(probe.Refused('not_a_public_enum')), 'unexpected_probe_error')
        ast.parse((HERE/'probe_asr_scheduling.py').read_bytes(),feature_version=(3,9))

    def fake_main(self, rows, after_completed=4):
        before=dict(memory=dict(completed=4),model_idle=True)
        after=dict(memory=dict(completed=after_completed),model_idle=True)
        guard=SimpleNamespace(ERROR_CODES=frozenset(),metadata=__import__('unittest.mock').mock.Mock(side_effect=[before,after]))
        args=['probe','--run','--pipeline-source','public-helper','--startup-sha256','public-pin',
              '--boot-id','public-boot','--ui-pid','2','--ui-birth','3','--camera-pid','4','--camera-birth','5']
        output=io.StringIO()
        with patch.object(probe,'load',return_value=guard),patch.object(probe,'run_child',side_effect=rows), \
             patch.object(sys,'argv',args),patch.object(sys,'stdout',output):
            code=probe.main()
        return code,json.loads(output.getvalue())

    def test_main_preserves_completed_slots_and_refuses_incomplete_comparison(self):
        code,value=self.fake_main([dict(nice=0),dict(nice=-5),probe.Refused('owned_child_timeout')])
        self.assertEqual(code,1);self.assertEqual(len(value['completed_results']),2)
        self.assertEqual(value['status'],'PUBLIC_ASR_SCHEDULING_INCOMPLETE_NO_GAIN')
        self.assertFalse(value['causal_gain_claimed'])

    def test_full_comparison_catches_transcript_or_between_slot_background_change(self):
        rows=[dict(nice=n,decode_ms=10,background_changed=False,same_as_warmup=True,public_result_sha256='public') for n in probe.ORDER]
        rows[1]['same_as_warmup']=False
        code,value=self.fake_main(rows)
        self.assertEqual(value['comparison_status'],'TRANSCRIPT_CHANGED_NO_GAIN_CLAIM')
        rows[1]['same_as_warmup']=True
        code,value=self.fake_main(rows,after_completed=5)
        self.assertEqual(value['comparison_status'],'BACKGROUND_CHANGED_NO_GAIN_CLAIM')


if __name__=='__main__':unittest.main()
