"""Short pure mocks. No proc, service, lock, GUI, model or device operation."""
import importlib.util
from pathlib import Path
import sys
import types
import unittest
from unittest import mock

ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
import restore_original_ui as c


class Tests(unittest.TestCase):
    def test_kernel_empty_argv_skips_and_malformed_nonempty_refuses(self):
        fields=['S','1']+['0']*18;fields[19]='2302'
        with mock.patch.object(Path,'read_text',return_value='2 (kernel) '+' '.join(fields)):
            with mock.patch.object(Path,'read_bytes',return_value=b''):
                self.assertIsNone(c.process(2))
            with mock.patch.object(Path,'read_bytes',return_value=b'not-null-terminated'):
                with self.assertRaises(ValueError):c.process(2)
            with mock.patch.object(Path,'read_bytes',return_value=b'/usr/bin/python3\0-B\0/test.py\0'):
                self.assertEqual(c.process(2)['birth'],'2302')
    def test_execstart_volatile_pid_and_timestamp_do_not_change_reviewed_argv(self):
        before='{ path=/usr/bin/python3 ; argv[]=/usr/bin/python3 -B /original.py --config /config.json ; start_time=[n/a] ; pid=0 ; }'
        after=before.replace('[n/a]','[new time]').replace('pid=0','pid=5000')
        self.assertEqual(c.exec_argv(before),c.exec_argv(after))
        self.assertNotEqual(c.exec_argv(before),c.exec_argv(after.replace('/original.py','/other.py')))
    def test_candidate_worker_is_not_ignored_after_gui_exit(self):
        with mock.patch.object(Path,'iterdir',return_value=[types.SimpleNamespace(name='2'),types.SimpleNamespace(name='9')]), \
             mock.patch.object(c,'process',side_effect=[None,dict(argv=['python',c.TARGET+'/runtime/aura/tools/gstreamer_audio_worker.py'])]):
            with self.assertRaises(ValueError):c.candidate_tree_gone()
    def test_natural_exit_recovery_is_explicit_honest_and_no_service_in_inspect(self):
        candidate=dict(owner=dict(pid=99,birth='1',cmdline_sha256='a'*64))
        with mock.patch.object(c,'lock',return_value=123),mock.patch.object(c.os,'close'), \
             mock.patch.object(c,'inactive',return_value=(dict(guard='/own/guard'),{})), \
             mock.patch.object(c,'candidate_owner',return_value=candidate), \
             mock.patch.object(c,'owner_gone'),mock.patch.object(c,'candidate_tree_gone'), \
             mock.patch.object(c,'command',side_effect=AssertionError('No service action in inspect')):
            with self.assertRaisesRegex(ValueError,'candidate_normal_close_receipt_required'):c.restore({})
            result=c.restore({},candidate_exited_naturally=True)
            self.assertIn('exit_code_unknown',result['candidate_exit_provenance'])
            self.assertIsNone(result['candidate_exit_code'])
            self.assertEqual(result['status'],'READY_TO_RESTORE_ORIGINAL_ONLY')
    def test_normal_receipt_path_stays_default_and_natural_does_not_forge_it(self):
        with mock.patch.object(c,'lock',return_value=123),mock.patch.object(c.os,'close'), \
             mock.patch.object(c,'inactive',return_value=(dict(guard='/own/guard'),{})), \
             mock.patch.object(c,'candidate_owner',return_value=dict(owner={})), \
             mock.patch.object(c,'owner_gone'),mock.patch.object(c,'candidate_tree_gone'), \
             mock.patch.object(c,'close_receipt') as receipt:
            result=c.restore({},'/owned/receipt','a'*64)
            self.assertEqual(result['candidate_exit_provenance'],'verified_normal_wm_delete_exit_receipt')
            receipt.assert_called_once()
    def test_lock_release_happens_before_original_start_and_only_own_guard_removed(self):
        events=[];props=dict(Restart='no',SendSIGKILL='yes',TimeoutStopUSec='25s',DropInPaths='/old.conf',
            ExecStart='{ argv[]=/usr/bin/python3 -B /original.py ; pid=0 ; }')
        journal=dict(guard=c.GUARD_ROOT+'/z-aura-yuki-capacity-20261030.conf',
            guard_sha256=c.digest(b'guard'),original_properties=props)
        unit=dict(props,MainPID='5000',ActiveState='active',Job='')
        policy=dict(old_supervisor=dict(argv=['/usr/bin/python3','-B','/original.py']))
        safe=dict(camera_pid=260102,pan_state='FAULT',pulse_us=None)
        with mock.patch.object(c,'lock',return_value=123), \
             mock.patch.object(c.os,'close',side_effect=lambda fd:events.append(('close_lock',fd))), \
             mock.patch.object(c,'inactive',return_value=(journal,{})),mock.patch.object(c,'candidate_owner',return_value=None), \
             mock.patch.object(c,'candidate_tree_gone'),mock.patch.object(c,'show',return_value=unit), \
             mock.patch.object(c,'process',return_value=dict(argv=policy['old_supervisor']['argv'])), \
             mock.patch.object(c,'safety',return_value=safe),mock.patch.object(c,'proof',return_value=(journal,unit)), \
             mock.patch.object(c,'read',return_value=b'guard'),mock.patch.object(c,'save'), \
             mock.patch.object(Path,'unlink',side_effect=lambda:events.append(('unlink_guard',))), \
             mock.patch.object(c,'command',side_effect=lambda args,**kw:events.append(tuple(args)) or ''):
            result=c.restore(policy,execute=True)
        self.assertLess(events.index(('close_lock',123)),events.index(('/bin/systemctl','--no-block','start',c.UNIT)))
        self.assertEqual(result['status'],'ORIGINAL_RESTORED_OWN_GUARD_REMOVED')
        self.assertEqual(events.count(('unlink_guard',)),1)
        self.assertFalse(any('stop' in event or 'kill' in event for event in events))


if __name__=='__main__':unittest.main(verbosity=2)
