"""Short injected round2 contracts; no real proc/socket/service/GUI calls."""
import ast
import hashlib
import io
import json
from pathlib import Path
import sys
import types
import unittest
from unittest import mock

ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
import control_round2 as c
import launch_round2 as launch
import port_wait


class Tests(unittest.TestCase):
    def test_port_wait_is_exact_original_pinned_ast_and70seconds(self):
        old=json.loads((ROOT.parent/'resume_ui_trial/actual_ui_baseline.json').read_text(encoding='utf-8'))
        source=old['launcher']['content']
        self.assertEqual(hashlib.sha256(source.encode()).hexdigest(),old['launcher']['sha256'])
        original=next(n for n in ast.parse(source).body if isinstance(n,ast.FunctionDef) and n.name=='check_port_unused')
        current=next(n for n in ast.parse((ROOT/'port_wait.py').read_text()).body if isinstance(n,ast.FunctionDef))
        self.assertEqual(ast.dump(original,include_attributes=False),ast.dump(current,include_attributes=False))
        self.assertEqual(ast.literal_eval(current.args.defaults[0]),70)
    def environment(self):
        events=[];spawned=[];saved=[];raw=b'public fixture'
        command=['/usr/bin/python3','-B',c.TARGET+'/runtime/aura/tools/board_avatar_pan.py','--evidence-root',c.TARGET+'/evidence/old']
        descriptor=dict(command=command,environment={},inherit_only_if_already_authorized=[],
            single_publisher_lock=c.LOCK,original_service=c.UNIT,microphone_initially_enabled=False,following_initially_enabled=False)
        policy=dict(launch_canonical_sha256=c.digest(c.encoded(descriptor)),inspection_sha256='a'*64,old_child={})
        manifest=dict(inspection_sha256='a'*64,data_origin='synthetic',
            candidate_files={str(i):dict(sha256=c.digest(raw)) for i in range(356)})
        def load(path):return descriptor if str(path).endswith('/launch.json') else manifest
        def spawn(command,**kwargs):
            events.append('spawn');spawned.append((command,kwargs));return types.SimpleNamespace(pid=60001)
        def process(pid):return dict(pid=pid,birth='1',cmdline_sha256='b'*64,argv=spawned[-1][0])
        patches=[mock.patch.object(c,'lock',return_value=123),mock.patch.object(c.os,'close'),
            mock.patch.object(launch.os,'O_NOFOLLOW',0,create=True),
            mock.patch.object(c,'inactive',side_effect=lambda p:events.append('proof')),
            mock.patch.object(c,'close_receipt'),mock.patch.object(c,'candidate_tree_gone'),
            mock.patch.object(c,'load',side_effect=load),mock.patch.object(c,'read',return_value=raw),
            mock.patch.object(c,'save',side_effect=lambda path,value:saved.append((path,value))),
            mock.patch.object(c,'process',side_effect=process),
            mock.patch.object(launch,'check_port_unused',side_effect=lambda port,wait_seconds:events.append(('wait',port,wait_seconds))),
            mock.patch.object(launch.subprocess,'Popen',side_effect=spawn),
            mock.patch.object(launch.os,'open',return_value=456),
            mock.patch.object(launch.os,'fdopen',return_value=io.BytesIO())]
        return events,spawned,saved,policy,patches
    def run_launch(self,execute,change=False):
        from contextlib import ExitStack
        events,spawned,saved,policy,patches=self.environment()
        with ExitStack() as stack:
            for patch in patches:stack.enter_context(patch)
            if change:
                stack.enter_context(mock.patch.object(c,'inactive',side_effect=[None,ValueError('changed during wait')]))
            if change:
                with self.assertRaises(ValueError):launch.launch(policy,'/receipt','c'*64,execute=True)
                return events,spawned,saved,None
            result=launch.launch(policy,'/receipt','c'*64,execute=execute)
        return events,spawned,saved,result
    def test_default_launch_inspect_does_not_bind_or_spawn(self):
        events,spawned,saved,result=self.run_launch(False)
        self.assertFalse(any(isinstance(e,tuple) and e[0]=='wait' for e in events))
        self.assertEqual(spawned,[]);self.assertEqual(saved,[])
        self.assertEqual(result['status'],'READY_TO_LAUNCH_ONE_SYNTHETIC_GUI')
    def test_explicit_launch_waits70_then_reproves_before_spawn_and_inherits_lock(self):
        events,spawned,saved,result=self.run_launch(True)
        self.assertEqual(events,['proof',('wait',8783,70),'proof','spawn'])
        command,kwargs=spawned[0]
        self.assertEqual(kwargs['pass_fds'],(123,))
        self.assertEqual(command[command.index('--evidence-root')+1],c.CONTROL+'/evidence/gui-capacity-round2')
        self.assertEqual(result['evidence_root'],c.CONTROL+'/evidence/gui-capacity-round2')
        self.assertEqual(saved[0][0],c.CONTROL+'/candidate_owner.json')
    def test_source_or_guard_change_during_wait_prevents_spawn(self):
        events,spawned,saved,_=self.run_launch(True,change=True)
        self.assertEqual(spawned,[]);self.assertEqual(saved,[])
        self.assertIn(('wait',8783,70),events)
    def test_round2_scope_and_current_original_owner_are_fixed(self):
        policy=json.loads((ROOT/'policy.json').read_text())
        self.assertEqual(c.CONTROL,'/home/root/aura-board-owner-candidate-20261030/ui-capacity-control-20261030-r2')
        self.assertTrue(c.TARGET.endswith('/yuki-gui-capacity-20261030-r3'))
        self.assertEqual(policy['old_supervisor']['pid'],454995)
        self.assertEqual(policy['old_supervisor']['birth'],'1377730')
        self.assertEqual(policy['old_child']['pid'],455003)
        self.assertEqual(policy['old_child']['birth'],'1377851')
        x11=(ROOT/'x11_close.py').read_text()
        self.assertNotIn("('0','1296')",x11)
        self.assertIn("('0','454995')",x11)
    def test_alias_and_kernel_thread_fixes_reused_without_function_changes(self):
        def methods(path):
            return {node.name:ast.dump(node,include_attributes=False) for node in ast.parse(path.read_bytes()).body if isinstance(node,ast.FunctionDef)}
        old=methods(ROOT.parent/'resume_ui_trial/restore_v2.py');new=methods(ROOT/'control_round2.py')
        for name in ('read','read_policy','process','restore'):
            self.assertEqual(old[name],new[name])


if __name__=='__main__':unittest.main(verbosity=2)
