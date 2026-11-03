import bootstrap
import copy,hashlib,json,tempfile,unittest
from pathlib import Path
from board.vision.dpu_protection_handoff import restore_protection
from board.vision.dpu_vision_schedule import DpuVisionSchedule


class HandoffTests(unittest.TestCase):
    def seed(self):
        root=Path(__file__).resolve().parents[1]
        # Scalar synthetic reproduction of the completed faults, no private DB/images.
        events=[]
        for kind,guard,cap in ((1,1,0),(2,0,1)):
            events.append(dict(task_code=kind,event_sequence=kind,native_completed=1,native_attempts=1,
                native_status=0,native_failed=0,body_failed=0,diagnostic_finished=1,
                lease_started_mono_ns=90000000000,lease_release_decision_mono_ns=90100000000,
                hardcap_exceeded=cap,guard_exceeded=guard))
        jobs={name:dict(calls=10,skipped=2,overruns=1,budget_exceeded=1,estimated_budget_ms=30.,
            maximum_ms=40.,disabled=True) for name in ('yunet','sface')}
        return dict(schema='aura-dpu-protection-handoff-1',boot='fixture',source_pid=77,
            source_birth_ticks=10,captured_mono_ns=100000000000,source_unit_sha256='a'*64,
            source_manifest_sha256='b'*64,feature_inference=dict(requests=15,execution_attempts=10,completed=10,
                features_returned=10,deferred=5,slot_denials=2,expired_after_admission=0),
            schedule=dict(owner_fenced=False,owner_fault_reason=None,
                active=None,waiting_primary=0,budget_ms=20.,guard_ms=5.,optional=jobs,
                primary_calls=1000,primary_period_overruns=1,lease_sequence=2,diagnostic_failures=0,
                optional_diagnostics=dict(enabled=True,diagnostic_errors=0,fault_events=events,counters={}),
                yunet_recovery=dict(phase='LATCHED',reason='unsafe_or_unknown_completion',faults=1,
                    attempts=0,recoveries=0,attempts_in_window=0,probe_successes=0,cooldown_until_monotonic_s=0.)))

    def restore(self,folder,seed):
        p=Path(folder)/'seed.json';raw=json.dumps(seed).encode();p.write_bytes(raw)
        s=DpuVisionSchedule(yunet_recovery=True,sface_recovery=True,clock=lambda:110.)
        info=restore_protection(s,dict(path=str(p),sha256=hashlib.sha256(raw).hexdigest()),
            boot_id='fixture',clock_ns=lambda:110000000000)
        return s,info

    def test_preserves_yunet_latch_counters_and_requires_new_primary(self):
        with tempfile.TemporaryDirectory() as temp:
            s,info=self.restore(temp,self.seed())
            self.assertEqual(s.primary_calls,1000);self.assertEqual(s.primary_overruns,1)
            self.assertEqual(s.yunet_recovery.phase,'LATCHED');self.assertEqual(s.sface_recovery.phase,'COOLDOWN')
            self.assertFalse(s.recovery_probe_allowed('sface'));self.assertTrue(info['first_use'])
            with s.primary(111.):pass
            self.assertTrue(s.recovery_probe_allowed('sface'))
            self.assertTrue(s.jobs['yunet']['disabled']);self.assertEqual(s.jobs['sface']['overruns'],1)

    def test_second_same_boot_start_latches_instead_of_resetting_attempt_budget(self):
        with tempfile.TemporaryDirectory() as temp:
            self.restore(temp,self.seed());s,info=self.restore(temp,self.seed())
            self.assertFalse(info['first_use']);self.assertEqual(s.sface_recovery.phase,'LATCHED')
            self.assertEqual(s.sface_recovery.reason,'uncheckpointed_same_boot_restart')

    def test_clean_new_boot_keeps_real_counters_and_both_running(self):
        seed=self.seed();old=seed['schedule'];old['optional_diagnostics']['fault_events']=[]
        old['yunet_recovery'].update(phase='RUNNING',reason=None,faults=0)
        for row in old['optional'].values():row.update(disabled=False,overruns=0)
        with tempfile.TemporaryDirectory() as temp:
            s,info=self.restore(temp,seed)
            self.assertEqual(s.sface_recovery.phase,'RUNNING');self.assertEqual(s.yunet_recovery.phase,'RUNNING')
            self.assertEqual(info['mode'],'clean_same_boot');self.assertEqual(s.jobs['yunet']['calls'],10)
            s,_=self.restore(temp,seed)
            self.assertEqual(s.yunet_recovery.phase,'LATCHED');self.assertEqual(s.sface_recovery.phase,'LATCHED')

    def test_guard_sface_never_auto_recovers(self):
        seed=self.seed();seed['schedule']['optional_diagnostics']['fault_events'][1]['guard_exceeded']=1
        with tempfile.TemporaryDirectory() as temp:
            s,_=self.restore(temp,seed);self.assertEqual(s.sface_recovery.phase,'LATCHED')

    def test_missing_native_or_budget_history_fails_closed(self):
        for change in ('native','history','owner','boot','future','calls'):
            seed=self.seed()
            if change=='native':seed['schedule']['optional_diagnostics']['fault_events'][1]['native_status']=1
            if change=='history':seed['schedule']['yunet_recovery']['attempts']=1
            if change=='owner':seed['schedule']['owner_fenced']=True
            if change=='boot':seed['boot']='other'
            if change=='future':seed['captured_mono_ns']=120000000000
            if change=='calls':seed['schedule']['optional']['sface']['calls']=0
            with self.subTest(change=change),tempfile.TemporaryDirectory() as temp:
                with self.assertRaises(ValueError):self.restore(temp,seed)
