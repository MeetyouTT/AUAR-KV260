"""Control/data/fault tests only. No CDLL, source runtime or model is loaded."""
from dataclasses import dataclass
import gc
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import weakref

import equivalence_benchmark as b
import build_plan


def plan():
    return {'schema': b.SCHEMA, 'purpose': 'isolated_model_equivalence',
        'expected_boot_id': '008f3e1b-c627-4b98-b120-d2a460cdbcbe', 'camera_service': b.SERVICE,
        'cases': list(b.CASES), 'primary_period_ns': 100_000_000, 'yolo_geometry': [640, 480, 1920],
        'models': [{'task': 'yunet', 'source_ttl_ns': 500_000_000},
                   {'task': 'sface', 'source_ttl_ns': 500_000_000}],
        'yolo_owner_config': {'classes': ['person'], 'score_threshold': .3,
            'person_nms_iou': .45, 'arch_fingerprint': '0x101000056010407'}}


def metadata(task):
    inputs = [{'name': task + '_input', 'dims': [1, 320, 320, 3] if task == 'yunet' else [1, 112, 112, 3],
               'dtype': 'xint8', 'fix_point': 7}]
    shapes = [[1, 40, 40, 51], [1, 20, 20, 34], [1, 10, 10, 34], [1, 5, 5, 51]] if task == 'yunet' else [[1, 128]]
    return inputs, [{'name': task + '_head_' + str(i), 'dims': dims, 'dtype': 'xint8', 'fix_point': 5}
                    for i, dims in enumerate(shapes)]


def raw_outputs(source, metas):
    return {m['name']: bytes([(sum(source[:64]) + sum(map(ord, m['name']))) % 256]) * b.byte_count(m) for m in metas}


def rows(source):
    return ((1., 2., 3., 4., .9, 0.),) if any(source[:64]) else ()


class Clock:
    def __init__(self):self.now = 1_000_000_000_000
    def __call__(self):self.now += 100_000;return self.now


class Guard:
    def __init__(self, blocked=False):self.blocked = blocked;self.calls = 0
    def check(self):
        self.calls += 1
        if self.blocked:raise b.Blocked('Production camera is active')
        return {'active_state': 'inactive', 'main_pid': 0}


class Owner:
    def __init__(self):self.ownership = object();self.handle = 771;self.closed = 0
    def close(self):self.closed += 1;self.ownership = None;self.handle = None


@dataclass
class Execution:
    report: dict
    outputs: tuple
    returned_mono_ns: int
    source_expires_ns: int
    @property
    def native_usable(self):
        return (self.report['outcome'] == 0 and self.report['submitted'] == self.report['completed'] == 1
                and not self.report['hardcap'] and not self.report['guard'] and self.report['native_status'] == 0)
    @property
    def usable(self):return self.native_usable and self.report['business_ready']


class Context:
    def __init__(self, deps, owner):
        self.deps, self.owner = deps, owner
        self.quarantined = False;self.adopted = False;self.closed = 0;self.primary = 0;self.acks = 0
    def restore_seed(self, seed):
        if seed.get('purpose') != 'isolated_model_equivalence':raise ValueError('bad seed')
    def adopt_yolo(self):self.owner.handle = None;self.adopted = True
    def snapshot(self):
        return dict(abi_version=2, seed_loaded=1, fenced=False, active=False,
            admissions=[0,0,0], overruns=[0,0,0], completed=[0,0,0], native_failures=[0,0,0],
            not_submitted=[0,0,0], disabled=[0,0,0], primary_calls=self.primary, primary_period_overruns=0,
            recovery=[dict(phase=0,faults=0,attempts=0,recoveries=0,attempt_count=0,history_opaque=0)]*2)
    def result(self, output, task, expires):
        now = self.deps.clock()
        return Execution(dict(task=task,outcome=0,submitted=1,completed=1,native_status=0,
            hardcap=False,guard=False,business_ready=True,result_token=0,
            start_ns=now,native_return_ns=now+1000,release_decision_ns=now+2000),output,now+3000,expires)
    def execute_yolo(self, source, **kw):
        assert self.adopted
        self.primary += 1
        self.deps.events.append('native_yolo')
        return self.result(rows(source),0,kw['source_expires_ns'])
    def confirm_result(self, result):self.acks += 1;return result
    def close(self):
        if self.deps.mode == 'close_unknown':raise KeyboardInterrupt()
        self.closed += 1;self.owner.close()


class Old:
    def __init__(self, deps, task):
        self.deps,self.task = deps,task;self.inputs,self.outputs=metadata(task);self.closed=0;self.calls=0
    def execute_raw(self, source):
        self.calls += 1;self.deps.events.append('old:' + self.task)
        if self.deps.mode == 'legacy_unknown':raise b.UnsafeRetained('injected old wait failure')
        return b.LegacyResult(raw_outputs(source,self.outputs),1000)
    def close(self):self.closed += 1


class New:
    def __init__(self, deps, context, task):
        self.deps,self.context,self.task=deps,context,task
        self.inputs,self.outputs=metadata(task);self.outputs.reverse();self.closed=0;self.calls=0
    def execute_encoded(self, source, **kw):
        self.calls += 1;self.deps.events.append('new:' + self.task)
        if self.deps.mode == 'native_unknown':
            self.context.quarantined=True;raise b.UnsafeRetained('injected native unknown')
        if self.deps.mode == 'native_interrupt':raise KeyboardInterrupt()
        values=raw_outputs(source,self.outputs)
        if self.deps.mode == 'mismatch':
            key=self.outputs[0]['name'];values[key]=b'!' + values[key][1:]
        result=self.context.result(tuple(values[m['name']] for m in self.outputs),
            1 if self.task=='yunet' else 2,kw['source_expires_ns'])
        if self.deps.mode in ('hardcap','guard'):result.report[self.deps.mode]=True
        if self.deps.mode=='denied':result.report.update(outcome=1,submitted=0,completed=0,native_status=-1)
        return result
    def close(self):self.closed += 1


class Dependencies:
    def __init__(self, clock, mode='ok'):
        self.clock,self.mode=clock,mode;self.events=[];self.created=0;self.old=[];self.new=[]
    def owner(self):self.created+=1;self.owned=Owner();return self.owned
    def legacy_yolo(self, owner, source):
        assert owner.handle == 771  # Never use a borrowed handle after adopt.
        self.events.append('legacy_yolo')
        if self.mode=='legacy_yolo_unknown':raise b.UnsafeRetained('startup native unknown')
        return rows(source),1000
    def context(self, owner):self.ctx=Context(self,owner);return self.ctx
    def maintenance_seed(self, now):return {'purpose':'isolated_model_equivalence'}
    def legacy(self, owner, spec):
        value=Old(self,spec['task']);self.old.append(value);return value
    def native_runner(self, context, spec):
        value=New(self,context,spec['task']);self.new.append(value);return value


class FakeArray:
    def __init__(self, source):self.storage=bytearray(source)
    def copy(self):return FakeArray(self.storage)
    def reshape(self, _dims):return self
    def tobytes(self):return bytes(self.storage)


class FakeNP:
    int8='int8'
    def frombuffer(self, source, **kw):return FakeArray(source)
    def empty(self, dims, **kw):
        size=1
        for d in dims:size*=d
        return FakeArray(bytes(size))


class FakeVart:
    def __init__(self, status=0, throw=False):self.status,self.throw=status,throw
    def execute_async(self, inputs, outputs):
        if self.throw:raise RuntimeError('unconfirmed execute')
        outputs[0].storage[:]=b'\x2a'*len(outputs[0].storage)
        return 7
    def wait(self, job):assert job==7;return self.status


class Tests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.addCleanup(b._UNSAFE_HOLD.clear)
    def bench(self, mode='ok', guard=None, journal=None):
        clock=Clock();deps=Dependencies(clock,mode)
        bench=b.Benchmark(plan(),deps,guard or Guard(),journal or b.Journal(self.temp.name),clock)
        return bench,deps
    def test_all_int8_bytes_equal_by_tensor_name_with_reversed_new_ports(self):
        bench,deps=self.bench();result=bench.run()
        self.assertTrue(result['passed']);self.assertTrue(result['cleanup_confirmed']);self.assertFalse(result['unsafe'])
        self.assertEqual(len(result['pairs']),6)
        self.assertEqual(result['primary_anchors'],4)
        self.assertEqual(result['completed_calls'],dict(legacy_yolo=2,native_yolo=6,legacy_optional=4,native_optional=4))
        self.assertEqual(deps.events[:2],['legacy_yolo','legacy_yolo'])
        self.assertEqual(deps.owned.closed,1)
        self.assertTrue(all(row['byte_equal'] for row in result['pairs']))
        rendered=json.dumps(result)
        self.assertNotIn('source_array',rendered);self.assertNotIn('raw_output_values',rendered)
        self.assertFalse(result['accuracy_evaluated']);self.assertFalse(result['utilization_or_speedup_evaluated'])
    def test_active_service_blocks_before_any_owner_creation(self):
        bench,deps=self.bench(guard=Guard(blocked=True))
        with self.assertRaises(b.Blocked):bench.run()
        self.assertEqual(deps.created,0)
    def test_mismatch_stops_next_case_and_closes_confirmed_resources(self):
        bench,deps=self.bench('mismatch');result=bench.run()
        self.assertFalse(result['passed']);self.assertFalse(result['unsafe']);self.assertTrue(result['cleanup_confirmed'])
        self.assertEqual(len(deps.old),1);self.assertEqual(deps.new[0].calls,1)
        self.assertGreater(result['pairs'][-1]['raw_tensors'][0]['differing_bytes']+
            sum(r['differing_bytes'] for r in result['pairs'][-1]['raw_tensors'][1:]),0)
    def test_hardcap_stops_without_recovery_or_further_empty_calls(self):
        bench,deps=self.bench('hardcap');result=bench.run()
        self.assertFalse(result['passed']);self.assertTrue(result['cleanup_confirmed'])
        self.assertEqual(deps.new[0].calls,1);self.assertEqual(len(deps.new),1)
        self.assertEqual(deps.ctx.acks,0)
    def test_guard_stops_without_retry(self):
        bench,deps=self.bench('guard');result=bench.run()
        self.assertFalse(result['passed']);self.assertFalse(result['unsafe']);self.assertEqual(deps.new[0].calls,1)
    def test_ordinary_denial_stops_without_fallback(self):
        bench,deps=self.bench('denied');result=bench.run()
        self.assertFalse(result['passed']);self.assertEqual(deps.new[0].calls,1);self.assertEqual(deps.owned.closed,1)
    def test_old_wait_unknown_retains_all_resources(self):
        bench,deps=self.bench('legacy_unknown');result=bench.run()
        self.assertTrue(result['unsafe']);self.assertFalse(result['cleanup_confirmed'])
        self.assertEqual(deps.owned.closed,0);self.assertEqual(deps.old[0].closed,0)
        self.assertEqual(deps.new[0].closed,0);self.assertEqual(deps.new[0].calls,0)
        marker=json.loads((Path(self.temp.name)/'checkpoint.json').read_text())
        self.assertTrue(marker['unsafe']);self.assertTrue(marker['owner_must_remain_alive'])
    def test_native_unknown_retains_owner_buffers_and_no_next_case(self):
        bench,deps=self.bench('native_unknown');result=bench.run()
        self.assertTrue(result['unsafe']);self.assertEqual(deps.owned.closed,0)
        self.assertEqual(deps.old[0].closed,0);self.assertEqual(deps.new[0].closed,0)
        self.assertEqual(deps.new[0].calls,1)
    def test_native_interruption_is_conservatively_unconfirmed(self):
        bench,deps=self.bench('native_interrupt');result=bench.run()
        self.assertTrue(result['unsafe']);self.assertEqual(deps.owned.closed,0)
    def test_original_yolo_unknown_is_retained_before_adoption(self):
        bench,deps=self.bench('legacy_yolo_unknown');result=bench.run()
        self.assertTrue(result['unsafe']);self.assertEqual(deps.owned.closed,0);self.assertIsNone(bench.context)
    def test_close_unknown_never_falls_through_to_owner_close(self):
        bench,deps=self.bench('close_unknown');result=bench.run()
        self.assertTrue(result['unsafe']);self.assertFalse(result['passed']);self.assertEqual(deps.owned.closed,0)
    def test_unsafe_marker_io_failure_still_preserves_process_references(self):
        class FailingJournal(b.Journal):
            def write(self,value):
                if value['unsafe']:raise OSError('storage unavailable')
                super().write(value)
        bench,deps=self.bench('native_unknown',journal=FailingJournal(self.temp.name))
        result=bench.run();self.assertTrue(result['unsafe_marker_write_failed'])
        reference=weakref.ref(bench);key=id(bench);del bench;gc.collect()
        self.assertIsNotNone(reference());self.assertIn(key,b._UNSAFE_HOLD);self.assertEqual(deps.owned.closed,0)
    def test_byte_comparison_rejects_missing_name_or_wrong_size(self):
        with self.assertRaises(b.StopBenchmark):b.compare_bytes({'head':b'1'},{'other':b'1'})
        with self.assertRaises(b.StopBenchmark):b.compare_bytes({'head':b'1'},{'head':b'12'})
    def test_real_legacy_control_flow_raw_bytes_and_unknown_retention(self):
        class Tensor:
            name='head';dims=[1,4];dtype='xint8'
            def get_attr(self,name):return 7
        class Pinned:
            inputs=[Tensor()];outputs=[Tensor()]
            def __init__(self,status=0,throw=False):self.runner=FakeVart(status,throw);self.closed=False
            def close(self):self.closed=True
        pinned=Pinned();old=b.LegacyRaw(pinned,FakeNP());result=old.execute_raw(b'\x01\x02\x03\x04')
        self.assertEqual(result.outputs,{'head':b'****'});old.close();self.assertTrue(pinned.closed)
        for status,throw in [(1,False),(0,True)]:
            pinned=Pinned(status,throw);old=b.LegacyRaw(pinned,FakeNP())
            with self.assertRaises(b.UnsafeRetained):old.execute_raw(b'1234')
            self.assertIsNotNone(old.pending)
            with self.assertRaises(b.UnsafeRetained):old.close()
            self.assertFalse(pinned.closed)
    def test_system_guard_only_accepts_inactive_loaded_service_and_expected_boot(self):
        guard=b.SystemGuard(plan())
        with patch.object(b.os,'geteuid',return_value=0),patch.object(b.Path,'read_text',return_value=plan()['expected_boot_id']):
            with patch.object(b.subprocess,'run',return_value=SimpleNamespace(returncode=0,
                stdout='LoadState=loaded\nActiveState=inactive\nSubState=dead\nMainPID=0\n')) as call:
                self.assertEqual(guard.check()['main_pid'],0)
                self.assertEqual(call.call_args[0][0][:3],['systemctl','show',b.SERVICE])
            with patch.object(b.subprocess,'run',return_value=SimpleNamespace(returncode=0,
                stdout='LoadState=loaded\nActiveState=active\nSubState=running\nMainPID=1\n')):
                with self.assertRaises(b.Blocked):guard.check()
        with patch.object(b.os,'geteuid',return_value=0),patch.object(b.Path,'read_text',return_value='different-boot'):
            with self.assertRaises(b.Blocked):guard.check()
    def test_no_unknown_private_or_unbounded_inputs(self):
        bad=plan();bad['cases']=['camera_capture']
        with self.assertRaises(b.Blocked):b.validate_plan(bad)
        bad=plan();bad['primary_period_ns']=10000000000
        with self.assertRaises(b.Blocked):b.validate_plan(bad)
        bad=plan();bad['models'][0]['private_feature_vector']=[1,2,3]
        with self.assertRaises(b.Blocked):b.validate_plan(bad)
        bad=plan();bad['yolo_owner_config']['identity_database']='not permitted'
        with self.assertRaises(b.Blocked):b.validate_plan(bad)
        self.assertEqual(b.public_bytes(128,'public_prng_260'),b.public_bytes(128,'public_prng_260'))
    def test_missing_v2_api_is_blocked_before_library_or_model_creation(self):
        deps=b.RealDependencies.__new__(b.RealDependencies)
        deps.plan={'source_sets':{'candidate':{'resolved_root':self.temp.name},'legacy':{'resolved_root':self.temp.name}}}
        first,second=Path(self.temp.name)/'binding.py',Path(self.temp.name)/'protection.py'
        deps.pins={'candidate_binding':first,'candidate_protection':second}
        binding=SimpleNamespace(__file__=str(first),NativeContext=type('MissingV2',(),{}))
        protection=SimpleNamespace(__file__=str(second))
        with patch.object(b.sys,'path',list(b.sys.path)),patch.object(b.importlib,'import_module',side_effect=[binding,protection]),\
                patch.object(b.C,'CDLL') as library:
            with self.assertRaises(b.Blocked):deps.load()
            library.assert_not_called()
    def test_incomplete_candidate_import_is_explicitly_blocked_without_library(self):
        deps=b.RealDependencies.__new__(b.RealDependencies)
        deps.plan={'source_sets':{'candidate':{'resolved_root':self.temp.name},'legacy':{'resolved_root':self.temp.name}}}
        with patch.object(b.sys,'path',list(b.sys.path)),\
                patch.object(b.importlib,'import_module',side_effect=ImportError('not implemented yet')),\
                patch.object(b.C,'CDLL') as library:
            with self.assertRaises(b.Blocked):deps.load()
            library.assert_not_called()
    def test_plan_builder_hashes_complete_sources_without_loading_or_controlling_services(self):
        root=Path(self.temp.name);legacy,candidate=root/'old',root/'new'
        for base in (legacy,candidate):(base/'board/vision').mkdir(parents=True)
        for name in ('yolo_dpu.py','dpu_vision_runtime.py'):(legacy/'board/vision'/name).write_text('pass\n')
        for name in ('native_binding.py','native_protection.py'):(candidate/'board/vision'/name).write_text('pass\n')
        model=root/'yolo.xmodel';model.write_bytes(b'fake model')
        model.with_suffix('.prototxt').write_bytes(b'fake prototxt')
        old_library=root/'old.so';old_library.write_bytes(b'not ELF')
        bridge=root/'new.so';bridge.write_bytes(b'not ELF')
        snapshot=root/'snapshot.json';snapshot.write_text('{"scope":"test-only"}')
        owner=plan()['yolo_owner_config'];owner.update(model=str(model),model_sha256=b.sha256(model),
            model_config_sha256=b.sha256(model.with_suffix('.prototxt')),
            native_library=str(old_library),native_sha256=b.sha256(old_library))
        config=root/'owner.json';config.write_text(json.dumps(owner))
        rows=[]
        for task in ('yunet','sface'):
            path=root/(task+'.xmodel');path.write_bytes(b'not a model')
            manifest=root/(task+'.manifest.json');manifest.write_text('{}')
            rows.append(dict(task=task,model=str(path),manifest=str(manifest),source_ttl_ns=500_000_000))
        models=root/'models.json';models.write_text(json.dumps(rows));out=root/'prepared'
        with patch.object(b.C,'CDLL') as dll,patch.object(b.subprocess,'run') as processes:
            build_plan.main(['--legacy-root',str(legacy),'--candidate-root',str(candidate),'--bridge',str(bridge),
                '--production-snapshot',str(snapshot),'--expected-boot-id',plan()['expected_boot_id'],
                '--yolo-owner-config',str(config),'--optional-models',str(models),'--new-output-directory',str(out)])
            result=json.loads((out/'plan.json').read_text());ready=b.RealDependencies(result)
            self.assertFalse(ready.loaded);dll.assert_not_called();processes.assert_not_called()
        self.assertEqual(len(json.loads((out/'legacy-python-sources.json').read_text())['files']),2)
        self.assertEqual(result['artifacts']['bridge']['sha256'],b.sha256(bridge))
    def test_cli_unsafe_result_write_failure_still_enters_owner_hold(self):
        root=Path(self.temp.name);config=root/'plan.json';config.write_text(json.dumps(plan()))
        clock=Clock();deps=Dependencies(clock,'native_unknown');deps.load=lambda:None
        target=root/'actual-output'
        original_write=b.Path.write_text
        def write(path,*args,**kwargs):
            if path.name=='result.json':raise OSError('result storage unavailable')
            return original_write(path,*args,**kwargs)
        class Held(Exception):pass
        with patch.object(b,'SystemGuard',return_value=Guard()),patch.object(b,'RealDependencies',return_value=deps),\
                patch.object(b.Path,'write_text',write),patch.object(b.signal,'signal'),\
                patch.object(b,'hold_unsafe_owner',side_effect=Held) as hold:
            with self.assertRaises(Held):b.main(['--plan',str(config),'--output-directory',str(target),'--execute-maintenance'])
            self.assertEqual(hold.call_count,1)
        self.assertEqual(deps.owned.closed,0)
        self.assertTrue(json.loads((target/'checkpoint.json').read_text())['unsafe'])


if __name__=='__main__':unittest.main()
