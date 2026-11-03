"""Fake-clock/socket regressions plus an optional real Linux listener test."""
import ast
import errno
import io
import os
from pathlib import Path, PurePosixPath
import re
import socket
import types
import unittest
from unittest.mock import patch

from ownerless_port_wait import WAIT_HELPERS, patch_ownerless


def tcp_table(*rows):
    header='  sl  local_address rem_address st\n'
    return (header+''.join('0: '+address+':'+format(port,'04X')+' 00000000:0000 '+state+'\n'
        for address,port,state in rows)).encode('ascii')


class Clock:
    def __init__(self):
        self.now=0.0
        self.sleeps=[]

    def monotonic(self):
        return self.now

    def sleep(self,duration):
        self.sleeps.append(duration)
        self.now+=duration


class Harness:
    def __init__(self,outcomes=()):
        self.clock=Clock()
        self.outcomes=list(outcomes)
        self.always_busy=False
        self.binds=[]
        self.closed=0
        self.boot_calls=0
        self.show_calls=0
        self.boot_failure_call=None
        self.processes={}
        self.unit=lambda:dict(MainPID='0',ActiveState='inactive',Job='')
        self.tables={'tcp':tcp_table(),'tcp6':tcp_table()}
        self.module=types.SimpleNamespace(socket=self.make_socket,SOL_SOCKET=1,SO_REUSEADDR=2)
        harness=self

        class SyntheticPath:
            def __init__(self,value):
                self.path=PurePosixPath(value)

            def __truediv__(self,other):
                return SyntheticPath(str(self.path/other))

            def __str__(self):
                return str(self.path)

            @property
            def name(self):
                return self.path.name

            def iterdir(self):
                assert str(self.path)=='/proc'
                processes=harness.processes() if callable(harness.processes) else harness.processes
                return [SyntheticPath('/proc/'+str(pid)) for pid in processes]

            def read_bytes(self):
                assert self.path.name=='cmdline'
                processes=harness.processes() if callable(harness.processes) else harness.processes
                return processes[int(self.path.parent.name)]

            def open(self,mode):
                assert mode=='rb' and str(self.path.parent)=='/proc/net'
                data=harness.tables[self.path.name]
                if callable(data):data=data()
                if data is None:raise FileNotFoundError(str(self.path))
                return io.BytesIO(data)

        self.namespace=dict(Path=SyntheticPath,time=self.clock,re=re,
            c=types.SimpleNamespace(show=self.show),boot=self.boot,need=self.need,
            EXACT_TARGET='/reviewed/production')
        exec(compile(WAIT_HELPERS,'<fake-port-wait>','exec'),self.namespace)

    @staticmethod
    def need(value,code):
        if not value:raise ValueError(code)

    def boot(self):
        self.boot_calls+=1
        if self.boot_failure_call==self.boot_calls:raise ValueError('fresh_boot_changed')

    def show(self):
        self.show_calls+=1
        return self.unit()

    def make_socket(self):
        harness=self

        class Probe:
            def __enter__(self):return self

            def __exit__(self,*args):harness.closed+=1

            def setsockopt(self,*args):
                assert args==(1,2,1)

            def bind(self,address):
                harness.binds.append(address)
                error=harness.outcomes.pop(0) if harness.outcomes else errno.EADDRINUSE if harness.always_busy else None
                if error is not None:raise OSError(error,'synthetic socket condition')

        return Probe()

    def run(self,initial=None):
        with patch.dict('sys.modules',{'socket':self.module}):
            self.namespace['ownerless'](initial or dict(MainPID='0',ActiveState='inactive',Job=''))


class PortReleaseWait(unittest.TestCase):
    def test_free_port_returns_immediately_and_rechecks_owner(self):
        h=Harness();h.run()
        self.assertEqual([('127.0.0.1',8783)],h.binds)
        self.assertEqual([],h.clock.sleeps)
        self.assertEqual(2,h.boot_calls)
        self.assertEqual(1,h.closed)

    def test_time_wait_then_release_retries_without_extra_actions(self):
        h=Harness([errno.EADDRINUSE,errno.EADDRINUSE,None])
        h.tables['tcp']=tcp_table(('0100007F',8783,'06'))
        h.run()
        self.assertEqual(3,len(h.binds));self.assertEqual(3,h.closed)
        self.assertEqual([.25,.25],h.clock.sleeps)

    def test_persistent_non_listening_occupancy_has_70_second_bound(self):
        h=Harness();h.always_busy=True
        h.tables['tcp']=tcp_table(('0100007F',8783,'06'))
        with self.assertRaisesRegex(ValueError,'^control_port_release_timeout$'):h.run()
        self.assertEqual(70.0,h.clock.now)
        self.assertEqual(281,len(h.binds))
        self.assertEqual(len(h.binds),h.closed)

    def test_existing_ipv4_listener_is_rejected_without_waiting(self):
        h=Harness();h.tables['tcp']=tcp_table(('0100007F',8783,'0A'))
        with self.assertRaisesRegex(ValueError,'^control_port_has_active_listener$'):h.run()
        self.assertEqual([],h.binds);self.assertEqual([],h.clock.sleeps)

    def test_new_foreign_listener_is_rejected_immediately_after_bind_failure(self):
        h=Harness([errno.EADDRINUSE])
        h.tables['tcp']=lambda:tcp_table(('00000000',8783,'0A')) if h.binds else tcp_table()
        with self.assertRaisesRegex(ValueError,'^control_port_has_active_listener$'):h.run()
        self.assertEqual(1,len(h.binds));self.assertEqual([],h.clock.sleeps)

    def test_ipv6_listener_is_also_rejected(self):
        h=Harness();h.tables['tcp6']=tcp_table(('0'*32,8783,'0A'))
        with self.assertRaisesRegex(ValueError,'^control_port_has_active_listener$'):h.run()
        self.assertEqual([],h.binds)

    def test_other_port_listener_does_not_block(self):
        h=Harness();h.tables['tcp']=tcp_table(('0100007F',8790,'0A'))
        h.run();self.assertEqual(1,len(h.binds))

    def test_non_address_in_use_errors_are_not_retried(self):
        h=Harness([errno.EACCES])
        with self.assertRaises(OSError) as caught:h.run()
        self.assertEqual(errno.EACCES,caught.exception.errno)
        self.assertEqual([],h.clock.sleeps)

    def test_boot_change_during_wait_aborts(self):
        h=Harness([errno.EADDRINUSE]);h.boot_failure_call=2
        with self.assertRaisesRegex(ValueError,'^fresh_boot_changed$'):h.run()
        self.assertEqual(1,len(h.binds));self.assertEqual([.25],h.clock.sleeps)

    def test_unit_owner_appearing_during_wait_aborts(self):
        h=Harness([errno.EADDRINUSE])
        h.unit=lambda:dict(MainPID='77' if h.clock.now else '0',ActiveState='inactive',Job='')
        with self.assertRaisesRegex(ValueError,'^ownerless_failed_or_inactive_unit_required$'):h.run()
        self.assertEqual(1,len(h.binds))

    def test_gtk_owner_appearing_during_wait_aborts(self):
        h=Harness([errno.EADDRINUSE])
        h.processes=lambda:{77:b'/usr/bin/python3\0/reviewed/board_avatar_pan.py\0'} if h.clock.now else {}
        with self.assertRaisesRegex(ValueError,'^another_gtk_owner_exists$'):h.run()
        self.assertEqual(1,len(h.binds))

    def test_successful_bind_still_requires_fresh_owner_check(self):
        h=Harness()
        h.unit=lambda:dict(MainPID='77' if h.binds else '0',ActiveState='inactive',Job='')
        with self.assertRaisesRegex(ValueError,'^ownerless_failed_or_inactive_unit_required$'):h.run()
        self.assertEqual(1,h.closed)

    def test_initial_live_owner_never_probes_port(self):
        h=Harness()
        with self.assertRaisesRegex(ValueError,'^ownerless_failed_or_inactive_unit_required$'):
            h.run(dict(MainPID='9',ActiveState='active',Job=''))
        self.assertEqual([],h.binds);self.assertEqual(0,h.boot_calls)

    def test_disabled_ipv6_is_allowed_but_missing_tcp_fails_closed(self):
        h=Harness();h.tables['tcp6']=None;h.run()
        h=Harness();h.tables['tcp']=None
        with self.assertRaises(FileNotFoundError):h.run()
        self.assertEqual([],h.binds)

    def test_malformed_or_oversized_tcp_metadata_fails_closed(self):
        for data in (b'header\ninvalid\n',b'X'*2097153):
            h=Harness();h.tables['tcp']=data
            with self.subTest(size=len(data)),self.assertRaises(ValueError):h.run()
            self.assertEqual([],h.binds)

    def test_source_patch_changes_only_ownerless_and_adds_two_helpers(self):
        path=Path(__file__).resolve().parents[1]/'FROZEN_APPLY_REMOTE.py'
        original=path.read_text(encoding='utf8');candidate=patch_ownerless(original)
        ast.parse(candidate,feature_version=(3,9))
        old={n.name:n for n in ast.parse(original).body if isinstance(n,ast.FunctionDef)}
        new={n.name:n for n in ast.parse(candidate).body if isinstance(n,ast.FunctionDef)}
        self.assertEqual({'_ownerless_process_snapshot','_control_port_has_listener'},set(new)-set(old))
        for name in set(old)-{'ownerless'}:
            self.assertEqual(ast.dump(old[name],include_attributes=False),ast.dump(new[name],include_attributes=False),name)

    def test_different_ownerless_source_is_rejected(self):
        with self.assertRaisesRegex(ValueError,'ownerless_baseline_changed'):
            patch_ownerless('def ownerless(u):\n return\n')

    @unittest.skipUnless(os.name=='posix' and Path('/proc/net/tcp').is_file(),'Real listener check requires Linux procfs')
    def test_real_linux_listener_on_owned_ephemeral_port_is_detected(self):
        namespace=dict(Path=Path,re=re,need=Harness.need)
        exec(compile(WAIT_HELPERS,'<real-listener-check>','exec'),namespace)
        with socket.socket(socket.AF_INET,socket.SOCK_STREAM) as listener:
            listener.bind(('127.0.0.1',0));listener.listen(1)
            port=listener.getsockname()[1]
            self.assertTrue(namespace['_control_port_has_listener'](port))


if __name__=='__main__':
    unittest.main()
