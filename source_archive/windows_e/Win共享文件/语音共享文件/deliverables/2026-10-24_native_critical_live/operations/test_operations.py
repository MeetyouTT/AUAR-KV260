import copy
import ast
import hashlib
import importlib.util
import json
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

import boot_ops
from policy import benchmark_safe,condition,require_native_healthy,window_result


OLD='11111111-1111-4111-8111-111111111111'
NEW='22222222-2222-4222-8222-222222222222'


class Decisions(unittest.TestCase):
    def test_new_boot_blocks_normal_camera_and_gui_until_qualified(self):
        for stage in ['ARMED','MAINTENANCE','QUALIFIED','UNSAFE_HOLD','NATIVE_START_HOLD']:
            for role in ['camera','gui']:self.assertFalse(condition(OLD,NEW,stage,role))
        self.assertTrue(condition(OLD,NEW,'NATIVE_START','camera'))
        self.assertFalse(condition(OLD,NEW,'NATIVE_START','gui'))
        self.assertTrue(condition(OLD,NEW,'NATIVE_READY','gui'))

    def test_old_boot_arming_does_not_interrupt_running_services(self):
        for role in ['camera','gui']:
            for stage in ['PREPARED','ARMING','ARMED']:self.assertTrue(condition(OLD,OLD,stage,role))
        self.assertFalse(condition(OLD,OLD,'NATIVE_START','camera'))

    def test_live_or_unsafe_owner_never_allows_fallback(self):
        self.assertFalse(benchmark_safe({'cleanup_confirmed':True},None,0,True))
        self.assertFalse(benchmark_safe({'cleanup_confirmed':True,'unsafe':True},None,0,False))
        self.assertFalse(benchmark_safe(None,{'stage':'native_execute','completion_unconfirmed':True},1,False))
        self.assertFalse(benchmark_safe(None,None,1,False))

    def test_confirmed_cleanup_or_premodel_block_is_distinct(self):
        self.assertTrue(benchmark_safe({'cleanup_confirmed':True,'passed':False},None,1,False))
        self.assertTrue(benchmark_safe(None,{'stage':'finished_confirmed_idle','unsafe':False,'completion_unconfirmed':False},1,False))
        self.assertTrue(benchmark_safe(None,None,2,False))
        self.assertFalse(benchmark_safe(None,{'stage':'native_execute'},2,False))

    def test_window_reports_missing_sface_load_separately(self):
        before=dict(pid=3,detected=100,primary_overruns=2,faults={'yunet':0,'sface':0},gaps=0,sface_completed=4)
        after=dict(before,detected=700)
        report=window_result(before,after,60)
        self.assertTrue(report['short_window_passed'])
        self.assertFalse(report['sustained_three_model_load_verified'])
        after['sface_completed']=5
        self.assertTrue(window_result(before,after,60)['sustained_three_model_load_verified'])

    def test_window_rejects_process_or_counter_reset(self):
        before=dict(pid=3,detected=100,primary_overruns=2,faults={'yunet':2,'sface':1},gaps=0,sface_completed=4)
        with self.assertRaises(ValueError):window_result(before,dict(before,pid=4),60)
        with self.assertRaises(ValueError):window_result(before,dict(before,detected=2),60)
        self.assertFalse(window_result(before,dict(before,detected=700,primary_overruns=3),60)['short_window_passed'])


class FakeOps(boot_ops.Ops):
    def __init__(self,root):
        super().__init__(root);self.commands=[]
        self.properties={u:{'MainPID':'0','Result':'success','ExecMainStatus':'0'} for u in [boot_ops.CAMERA,boot_ops.GUI]}
        self.sample={'pid':9,'dpu_schedule':{'owner_fenced':False,'optional':{'yunet':{'disabled':True},'sface':{'disabled':True}}}}
    def verify(self):pass
    def props(self,unit):return self.properties[unit]
    def command(self,argv,timeout=15):self.commands.append(argv);return ''
    def health(self):return self.sample
    def paths(self):return {n:self.root/(n+'.conf') for n in ['camera','gui','execution','rescue_timer','rescue_service']}


class Lifecycle(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
        meta={'root':str(self.root),'source_boot':OLD,'tag':'test','old_camera_pid':9}
        (self.root/'meta.json').write_text(json.dumps(meta))
        (self.root/'state.json').write_text(json.dumps({'phase':'PREPARED','maintenance_started':False,'owned':{}}))
        self.ops=FakeOps(self.root)
        self.clock=patch.object(boot_ops,'boot',return_value=OLD);self.clock.start();self.addCleanup(self.clock.stop)

    def test_owned_files_refuse_collision_and_foreign_edits(self):
        target=self.root/'file.conf';self.ops.own_file(target,b'ours')
        with self.assertRaises(AssertionError):self.ops.own_file(target,b'replacement')
        target.write_bytes(b'changed by another operator')
        with self.assertRaises(AssertionError):self.ops.remove_own(target)
        self.assertTrue(target.exists())

    def test_arm_only_adds_owned_conditions_without_restart(self):
        self.ops.properties[boot_ops.CAMERA]['MainPID']='9'
        self.ops.arm()
        self.assertEqual(self.ops.state()['phase'],'ARMED')
        for name in ['camera','gui']:self.assertIn(b'ExecCondition=',self.ops.paths()[name].read_bytes())
        self.assertFalse(any('restart' in c or 'reboot' in c or 'stop' in c for c in self.ops.commands))

    def test_current_boot_rescue_does_nothing(self):
        self.ops.phase('ARMED')
        self.assertTrue(self.ops.rescue()['source_boot_no_action'])
        self.assertFalse(self.ops.commands)

    def test_new_boot_rescue_only_before_any_execution(self):
        self.ops.phase('MAINTENANCE',maintenance_started=True)
        with patch.object(boot_ops,'boot',return_value=NEW):
            self.assertTrue(self.ops.rescue()['no_owner_replacement'])
        self.assertFalse(self.ops.commands)

    def test_unsafe_benchmark_never_restores_original(self):
        self.ops.phase('UNSAFE_HOLD',maintenance_started=True,benchmark_cleanup_confirmed=False)
        with self.assertRaises(AssertionError):self.ops.restore_original()
        self.assertFalse(self.ops.commands)

    def test_fenced_native_owner_not_stopped_for_rollback(self):
        self.ops.phase('OBSERVATION_FAILED',maintenance_started=True)
        self.ops.sample['dpu_schedule']['owner_fenced']=True
        with self.assertRaises(AssertionError):self.ops.protected_rollback()
        self.assertFalse(self.ops.commands)

    def test_nonzero_native_exit_does_not_start_old_owner(self):
        self.ops.phase('OBSERVATION_FAILED',maintenance_started=True)
        self.ops.properties[boot_ops.CAMERA]['ExecMainStatus']='1'
        with self.assertRaises(AssertionError):self.ops.protected_rollback()
        self.assertFalse(any('start' in c for c in self.ops.commands))


class ActualEntry(unittest.TestCase):
    def launch(self,ui_source):
        temporary=tempfile.TemporaryDirectory();self.addCleanup(temporary.cleanup)
        root=Path(temporary.name)
        ui=root/'candidate/aura/board/vision/ui_camera_service.py';ui.parent.mkdir(parents=True)
        ui.write_text(ui_source)
        config=root/'proposed.json';config.write_text(json.dumps({'native_execution':{
            'checkpoint_output':str(root/'not-written-checkpoint.json')}}))
        meta={'source_boot':OLD,'candidate_root':str(root/'candidate'),'candidate_config':str(config),
              'candidate_ui_sha256':hashlib.sha256(ui.read_bytes()).hexdigest()}
        (root/'meta.json').write_text(json.dumps(meta))
        entry=root/'native_entry.py';entry.write_bytes((Path(__file__).parent/'native_entry.py').read_bytes())
        log=(root/'entry.log').open('w');self.addCleanup(log.close)
        process=subprocess.Popen([sys.executable,str(entry)],stdout=log,stderr=subprocess.STDOUT)
        self.addCleanup(lambda:process.kill() if process.poll() is None else None)
        return root,process

    def test_real_entry_runs_pinned_source_with_original_interval(self):
        root,child=self.launch("import sys\nassert abs(sys.getswitchinterval()-.001)<1e-9\n")
        self.assertEqual(child.wait(timeout=3),0)
        self.assertFalse(list(root.rglob('UNSAFE_OWNER_RETAINED.json')))

    def test_real_entry_retains_fake_uncertain_owner_and_ignores_SIGTERM(self):
        root,child=self.launch("import sys,types\nsys.modules['board.vision.native_binding']=types.SimpleNamespace(_RETAINED={1:object()})\nraise RuntimeError('fake uncertainty; no native dependency')\n")
        until=time.monotonic()+3
        while not list(root.rglob('UNSAFE_OWNER_RETAINED.json')) and time.monotonic()<until:time.sleep(.02)
        self.assertTrue(list(root.rglob('UNSAFE_OWNER_RETAINED.json')))
        child.send_signal(signal.SIGTERM);time.sleep(.05)
        self.assertIsNone(child.poll())
        # This fixture has no DPU/native code. Killing it only cleans up the test.
        child.kill();child.wait(timeout=2)

    def test_old_rollback_keeps_real_policy_latched_and_fault_counters(self):
        baseline=Path('/home/ghmd/aura-native-critical-20261024/coherent-baseline/aura')
        sys.path.insert(0,str(baseline));self.addCleanup(lambda:sys.path.remove(str(baseline)))
        from board.vision.dpu_vision_schedule import DpuVisionSchedule
        source=ast.parse((Path(__file__).parent/'rollback_entry.py').read_text())
        function=next(node for node in source.body if isinstance(node,ast.FunctionDef) and node.name=='protected')
        seed={'primary_calls':500,'primary_period_overruns':3,'admissions':[500,62491,755],
              'overruns':[0,5,3],'recovery':[{'faults':5,'attempts':4,'recoveries':4,'probe_successes':0},
                                         {'faults':3,'attempts':2,'recoveries':2,'probe_successes':0}]}
        env={'initialize':DpuVisionSchedule.__init__,'seed':seed,'aux':{'sface_counters':{'completed':755}},
             'pin':{'sha256':'1'*64},'pid':123,'document':{'previous_kernel_history':{'archive_sha256':'2'*64}}}
        exec(compile(ast.fix_missing_locations(ast.Module(body=[function],type_ignores=[])),'rollback-hook','exec'),env)
        schedule=DpuVisionSchedule.__new__(DpuVisionSchedule)
        env['protected'](schedule,yunet_recovery=True,sface_recovery=True)
        self.assertEqual(schedule.yunet_recovery.faults,5);self.assertEqual(schedule.sface_recovery.faults,3)
        for kind in ['yunet','sface']:
            self.assertTrue(schedule.disabled(kind));self.assertFalse(schedule.recovery_ready(kind))
        self.assertEqual(schedule.inherited_sface_counters['completed'],755)
        self.assertEqual(schedule.protection_handoff['native_snapshot'],seed)


if __name__=='__main__':unittest.main()
