"""Host-only adversarial checks of the real C extension; no board or DPU."""
import ctypes
import gc
import importlib.util
import os
from pathlib import Path
import select
import subprocess
import sysconfig
import threading
import time
import unittest

ROOT=Path(__file__).resolve().parents[1]
BUILD=Path(__file__).resolve().parent/'host-build'
extension=BUILD/('_aura_schedprobe'+sysconfig.get_config_var('EXT_SUFFIX'))
spec=importlib.util.spec_from_file_location('_aura_schedprobe',extension)
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)

def fd_count():return len(os.listdir('/proc/self/fd'))

class ProbeLifecycleTests(unittest.TestCase):
    def test_owner_fields_and_ordered_ten_numeric_fields(self):
        p=module.Probe()
        try:
            row=p.sample()
            self.assertEqual(p.owner,(os.getpid(),threading.get_native_id()))
            self.assertEqual(len(row),10);self.assertTrue(all(type(x) is int for x in row))
            self.assertEqual(row[0],threading.get_native_id())
            self.assertGreaterEqual(row[8],row[1]);self.assertGreaterEqual(row[9],row[2])
            self.assertTrue(all(x>=0 for x in row[3:8]))
        finally:p.close()

    def test_constructor_rejects_arguments_without_fd_leak(self):
        before=fd_count()
        for call in (lambda:module.Probe(1),lambda:module.Probe(path='ignored')):
            with self.assertRaises(TypeError):call()
        gc.collect();self.assertEqual(fd_count(),before)

    def test_partial_new_and_double_init_are_safe(self):
        p=module.Probe.__new__(module.Probe)
        self.assertEqual(p.owner,(0,0));self.assertTrue(p.closed)
        with self.assertRaises(RuntimeError):p.sample()
        p.__init__();owner=p.owner;before=fd_count()
        with self.assertRaises(RuntimeError):p.__init__()
        self.assertEqual(fd_count(),before);self.assertEqual(p.owner,owner);p.close()

    def test_close_is_idempotent_and_sampling_closed_rejects(self):
        p=module.Probe();p.close();p.close();self.assertTrue(p.closed)
        with self.assertRaises(RuntimeError):p.sample()
        with self.assertRaises(RuntimeError):p.__init__()

    def test_foreign_thread_sample_rejected_and_foreign_close_allowed(self):
        p=module.Probe();rows=[]
        def work():
            try:p.sample();rows.append('unexpected_success')
            except RuntimeError:rows.append('rejected')
            p.close()
        t=threading.Thread(target=work);t.start();t.join(2)
        self.assertFalse(t.is_alive());self.assertEqual(rows,['rejected']);self.assertTrue(p.closed)

    def test_repeated_reads_and_foreign_thread_dealloc_release_one_fd(self):
        before=fd_count();p=module.Probe();self.assertEqual(fd_count(),before+1)
        for _ in range(1000):p.sample()
        self.assertEqual(fd_count(),before+1)
        holder=[p];del p
        t=threading.Thread(target=holder.clear);t.start();t.join(2)
        self.assertFalse(t.is_alive());gc.collect();self.assertEqual(fd_count(),before)

    @unittest.skipUnless(hasattr(os,'fork'),'Linux fork check')
    def test_fork_child_rejects_parent_probe_and_parent_remains_usable(self):
        p=module.Probe();reader,writer=os.pipe();pid=os.fork()
        if pid==0:
            os.close(reader)
            try:
                try:p.sample();data=b'UNEXPECTED'
                except RuntimeError:data=b'REJECTED'
                p.close();os.write(writer,data)
            finally:os.close(writer);os._exit(0)
        os.close(writer)
        try:
            ready,_,_=select.select([reader],[],[],3)
            self.assertTrue(ready);self.assertEqual(os.read(reader,32),b'REJECTED')
            waited,status=os.waitpid(pid,0);self.assertEqual(waited,pid);self.assertEqual(status,0)
            self.assertEqual(p.sample()[0],threading.get_native_id())
        finally:os.close(reader);p.close()

    def test_known_sleep_is_observed_without_claiming_gil_root(self):
        p=module.Probe()
        try:
            a=p.sample();time.sleep(.01);b=p.sample()
            self.assertGreaterEqual(b[1]-a[8],5_000_000)
            self.assertGreaterEqual(b[6]-a[6],1)
        finally:p.close()

class ParserTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # The exact production static parser is exposed only by this test build.
        source=BUILD/'parser_harness.c';target=BUILD/'parser_harness.so'
        source.write_text('#include '+repr(str(ROOT/'schedprobe.c')).replace("'",'"')+
                          '\nint review_parse(const char *p, size_t n, uint64_t *v) { return parse_counters(p,n,v); }\n')
        subprocess.run(['gcc','-std=c11','-O2','-fPIC','-shared','-I'+sysconfig.get_path('include'),str(source),'-o',str(target)],check=True,capture_output=True)
        cls.lib=ctypes.PyDLL(str(target));cls.lib.review_parse.argtypes=[ctypes.c_void_p,ctypes.c_size_t,ctypes.POINTER(ctypes.c_uint64)]
        cls.lib.review_parse.restype=ctypes.c_int
    def parse(self,data):
        output=(ctypes.c_uint64*3)();code=self.lib.review_parse(data,len(data),output)
        return code,tuple(output)
    def test_valid_whitespace_and_uint64_max(self):
        for data,expected in ((b'1 2 3\n',(1,2,3)),(b'\t0\n0 0\n',(0,0,0)),
                              (b'18446744073709551615 2 3',(2**64-1,2,3))):
            self.assertEqual(self.parse(data),(0,expected))
    def test_malformed_missing_extra_overflow_nul_and_oversize_reject(self):
        for data in (b'',b'1 2',b'1 2 3 4',b'-1 2 3',b'+1 2 3',b'1 0x2 3',
                     b'18446744073709551616 2 3',b'1 2 3\0',b'1 2 3'+b' '*252):
            with self.subTest(data=data[:40]):self.assertLess(self.parse(data)[0],0)

if __name__=='__main__':unittest.main(verbosity=2)
