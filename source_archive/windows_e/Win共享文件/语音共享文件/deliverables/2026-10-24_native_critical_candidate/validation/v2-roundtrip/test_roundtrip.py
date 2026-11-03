"""Actual CDLL/C++ ABI with fake model dependencies and deterministic clock."""
import ctypes as C
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch

sys.path.insert(0,os.environ['AURA_ROUNDTRIP_CANDIDATE'])
from board.vision import native_binding as b
from board.vision.native_protection import isolated_maintenance_seed


def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()


class Owner:
    fingerprint=b.FINGERPRINT
    def __init__(self,library):
        self.config={'native_library':str(library),'native_sha256':sha(library)}
        self.ownership=library.open('rb')
        self.handle=771
        self.lock=threading.Lock()
        self.destroyed=[]
    def close(self):
        with self.lock:
            if self.handle:self.destroyed.append(self.handle);self.handle=None
            if self.ownership:self.ownership.close();self.ownership=None


class Roundtrip(unittest.TestCase):
    def setUp(self):
        self.library=Path(os.environ['AURA_ROUNDTRIP_DSO'])
        self.lib=C.CDLL(str(self.library))
        self.lib.aura_fixture_now.restype=C.c_uint64
        self.lib.aura_fixture_advance.argtypes=[C.c_uint64]
        self.lib.aura_fixture_delay.argtypes=[C.c_uint64]
        self.lib.aura_fixture_delay(1_000_000)
        self.lib.aura_fixture_advance(2_000_000_000)
        self.owner=Owner(self.library)
        self.addCleanup(self.owner.close)
        self.context=b.NativeContext(self.owner,self.library,sha(self.library))
        self.assertEqual(self.lib.aura_fixture_fake_only(),2)
        self.clock=patch.object(b.time,'monotonic_ns',side_effect=lambda:self.lib.aura_fixture_now())
        self.clock.start();self.addCleanup(self.clock.stop)
        self.tmp=tempfile.TemporaryDirectory(prefix='aura-v2-test-')
        self.addCleanup(self.tmp.cleanup)
        self.models=[]
        self.context.restore_seed(isolated_maintenance_seed(
            boot_id=Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
            captured_mono_ns=self.now(),production_snapshot_sha256='a'*64))
        self.context.adopt_yolo()

    def now(self): return self.lib.aura_fixture_now()
    def advance(self,value): self.lib.aura_fixture_advance(value)
    def expires(self): return self.now()+1_000_000_000
    def primary(self,**kwargs):
        return self.context.execute_yolo(bytes(12),width=2,height=2,stride=6,
            source_expires_ns=kwargs.get('expires',self.expires()),
            primary_finish_ns=kwargs.get('finish',self.now()+100_000_000))
    def runner(self,task='sface'):
        directory=Path(self.tmp.name)/task;directory.mkdir(exist_ok=True)
        model=directory/'fake.tag';model.write_text('not a model')
        if task=='sface':
            shape=[1,112,112,3]
            outputs=[dict(name='sface_output',dims=[1,128],dtype='xint8',fix_point=5)]
        else:
            shape=[1,320,320,3]
            outputs=[dict(name='yunet_'+str(n),dims=[1,n,n,c],dtype='xint8',fix_point=7)
                     for n,c in ((40,51),(20,34),(10,34),(5,51))]
        manifest=directory/'manifest.json'
        manifest.write_text(json.dumps(dict(sha256=sha(model),partitions=[dict(
            device='DPU',fingerprint=b.FINGERPRINT,
            inputs=[dict(name=task+'_input',dims=shape,dtype='xint8',fix_point=7)],outputs=outputs)])))
        self.lib.aura_fixture_kind(1 if task=='yunet' else 2)
        runner=b.NativeRunner(self.context,task,model,sha(model),manifest,sha(manifest))
        self.models.append(runner)
        return runner
    def optional(self,runner,value=42,expires=None):
        return runner.execute_encoded(bytes([value])*runner._bytes(runner.inputs[0]),
            source_expires_ns=self.expires() if expires is None else expires)
    def close_all(self):
        for runner in self.models:runner.close()
        self.context.close()
    def probation(self,runner):
        self.primary();self.lib.aura_fixture_delay(31_000_000)
        fault=self.optional(runner)
        self.assertEqual(fault.report['hardcap'],1)
        self.assertEqual(fault.report['guard'],0)
        self.assertFalse(fault.usable)
        self.advance(10_000_000_000)
        self.lib.aura_fixture_delay(1_000_000)
        self.primary()
        return fault

    def test_exact_ABI_structures(self):
        expected=[(b.Report,'report',88),(b.Ack,'ack',32),(b.Recovery,'recovery',104),
                  (b.State,'state',432),(b.Seed,'seed',520)]
        for structure,name,size in expected:
            self.assertEqual(C.sizeof(structure),size)
            self.assertEqual(getattr(self.lib,'aura_native_'+name+'_size')(),size)
        self.assertEqual(self.context.snapshot()['seed_loaded'],1)
        self.close_all()

    def test_SFace_exact_encoded_bytes_and_signed_extremes(self):
        runner=self.runner();self.primary()
        for value in (0,42,127,128,255):
            result=self.optional(runner,value)
            self.assertEqual(result.outputs,(bytes([value])*128,))
            self.assertTrue(result.usable)
            self.assertEqual(result.report['completed'],1)
        self.assertEqual(self.context.snapshot()['completed'][2],5)
        self.close_all()

    def test_YuNet_four_ports_exact_bytes(self):
        runner=self.runner('yunet');self.primary()
        result=self.optional(runner,42)
        for i,(output,meta) in enumerate(zip(result.outputs,runner.outputs)):
            self.assertEqual(output,bytes([42+i])*runner._bytes(meta))
        self.assertTrue(result.usable)
        self.close_all()

    def test_YOLO_ownership_single_destroy_and_confirmed_rows(self):
        before=self.lib.aura_fixture_destroyed()
        result=self.primary()
        self.assertTrue(result.usable)
        self.assertEqual(result.outputs[0][:4],(1.,2.,3.,4.))
        self.owner.close();self.assertFalse(self.owner.destroyed)
        self.context.close()
        self.assertEqual(self.lib.aura_fixture_destroyed(),before+1)

    def test_three_post_GIL_ACKs_and_token_replay(self):
        runner=self.runner();self.probation(runner)
        for count in range(1,4):
            result=self.optional(runner)
            self.assertTrue(result.native_usable)
            self.assertFalse(result.usable)
            self.assertEqual(result.outputs,(b'*'*128,))
            self.assertGreater(result.report['result_token'],0)
            with self.assertRaises(b.BridgeError):runner.close()
            confirmed=self.context.confirm_result(result)
            self.assertEqual(confirmed.usable,count==3)
            state=self.context.snapshot()['recovery'][1]
            self.assertEqual(state['probe_successes'],count)
            self.assertEqual(state['recoveries'],int(count==3))
            replay=self.context.confirm_result(result)
            self.assertFalse(replay.usable)
            self.assertEqual(self.context.snapshot()['recovery'][1]['probe_successes'],count)
        self.close_all()

    def test_expired_after_native_before_Python_ACK_never_counts_probe(self):
        runner=self.runner();self.probation(runner)
        result=self.optional(runner)
        self.advance(1_000_000_000)
        self.assertFalse(result.native_usable)
        ack=self.context.confirm_result(result)
        self.assertFalse(ack.usable)
        self.assertEqual(self.context.snapshot()['recovery'][1]['probe_successes'],0)
        self.close_all()

    def test_pending_SFace_does_not_hold_primary_gate(self):
        runner=self.runner();self.probation(runner)
        result=self.optional(runner)
        self.assertTrue(self.primary().usable)
        rejected=self.optional(runner)
        self.assertEqual(rejected.report['submitted'],0)
        self.assertFalse(rejected.outputs)
        self.context.confirm_result(result)
        self.close_all()

    def test_primary_deadline_rejection_counts_late_cycle(self):
        runner=self.runner();self.probation(runner)
        pending=self.optional(runner)
        self.assertGreater(pending.report['result_token'],0)
        self.assertEqual(self.context.snapshot()['recovery'][1]['phase'],2)
        before=self.context.snapshot()
        result=self.primary(finish=self.now()-1)
        after=self.context.snapshot()
        self.assertFalse(result.usable)
        self.assertEqual(result.report['submitted'],0)
        self.assertEqual(after['primary_calls'],before['primary_calls']+1)
        self.assertEqual(after['primary_period_overruns'],before['primary_period_overruns']+1)
        self.assertEqual(after['not_submitted'][0],before['not_submitted'][0]+1)
        self.assertEqual(after['recovery'][1]['phase'],3)
        self.assertEqual(after['recovery'][1]['reason'],5)
        self.assertFalse(self.context.confirm_result(pending).usable)
        self.assertEqual(self.context.snapshot()['recovery'][1]['phase'],3)
        self.close_all()

    def test_source_TTL_reject_before_native_and_return_access_recheck(self):
        runner=self.runner();self.primary()
        result=self.optional(runner,expires=self.now())
        self.assertEqual(result.report['submitted'],0)
        self.assertEqual(self.context.snapshot()['completed'][2],0)
        result=self.optional(runner)
        self.assertTrue(result.usable)
        self.advance(1_000_000_000)
        self.assertFalse(result.usable)
        self.assertEqual(result.report['completed'],1)
        self.close_all()

    def test_unknown_native_fence_no_outputs_and_retained_close(self):
        runner=self.runner();self.primary();self.lib.aura_fixture_fail_next()
        with self.assertRaises(b.CompletionUnknown):self.optional(runner)
        state=self.context.snapshot()
        self.assertEqual(state['fenced'],1)
        self.assertEqual(state['native_failures'][2],1)
        self.assertIn(id(self.context),b._RETAINED)
        with self.assertRaises(b.CompletionUnknown):runner.close()
        with self.assertRaises(b.CompletionUnknown):self.context.close()

    def test_checkpoint_seals_exact_history_and_new_context_appends(self):
        runner=self.runner();self.primary();self.optional(runner)
        before=self.context.snapshot()
        checkpoint=self.context.checkpoint('b'*64)
        self.assertEqual(checkpoint['checkpoint_kind'],1)
        self.assertEqual(checkpoint['source_pid'],os.getpid())
        self.assertEqual(self.context.snapshot()['quiesced'],1)
        refused=self.primary();self.assertEqual(refused.report['outcome'],10)
        refused=self.optional(runner);self.assertEqual(refused.report['outcome'],10)
        runner.close();self.context.close()
        # Fake factory alone permits another context in this host test process.
        # Real factory's one-context-per-process guard is tested separately by C++.
        owner2=Owner(self.library);self.addCleanup(owner2.close)
        target=b.NativeContext(owner2,self.library,sha(self.library))
        target.restore_seed(checkpoint);target.adopt_yolo()
        restored=target.snapshot()
        for name in ('admissions','completed','overruns','primary_calls','primary_period_overruns'):
            self.assertEqual(restored[name],before[name])
        result=target.execute_yolo(bytes(12),width=2,height=2,stride=6,
            source_expires_ns=self.expires(),primary_finish_ns=self.now()+100_000_000)
        self.assertTrue(result.usable)
        self.assertEqual(target.snapshot()['primary_calls'],before['primary_calls']+1)
        target.close()

    def test_CDLL_GIL_release_observed_inside_compiled_call(self):
        stop=threading.Event()
        def other():
            while not stop.is_set():self.lib.aura_fixture_try_progress()
        thread=threading.Thread(target=other);thread.start()
        try:
            self.lib.aura_fixture_block()
            self.assertGreaterEqual(self.lib.aura_fixture_progress(),10)
        finally:stop.set();thread.join(timeout=1)
        self.close_all()


if __name__=='__main__':unittest.main()
