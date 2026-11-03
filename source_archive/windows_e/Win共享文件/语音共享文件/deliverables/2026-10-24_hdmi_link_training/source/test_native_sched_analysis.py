import unittest
from native_sched_analysis import scheduler_window,parse_scheduler_events,matching_fault_report


def switch(ms,prev,next,state='S',cpu=0):
    return dict(kind='sched_switch',mono_ns=int(ms*1e6),prev_tid=prev,next_tid=next,prev_state=state,cpu=cpu)
def wake(ms,tid):return dict(kind='sched_wakeup',mono_ns=int(ms*1e6),tid=tid,cpu=1)


class AnalysisTests(unittest.TestCase):
    def test_preemption_is_runnable_time(self):
        events=[switch(0,2,1),switch(2,1,2,'R+'),switch(24,2,1)]
        r=scheduler_window(events,1,1_000_000,26_000_000)
        self.assertEqual(r['state_ms'],dict(RUNNING=3.,RUNNABLE=22.,BLOCKED=0.,UNKNOWN=0.))
        self.assertEqual(r['classification'],'RUNQUEUE_DOMINATED')

    def test_wakeup_separates_sleep_from_cpu_queue(self):
        events=[switch(0,2,1),switch(2,1,2,'S'),wake(22,1),switch(25,2,1)]
        r=scheduler_window(events,1,1_000_000,26_000_000)
        self.assertEqual(r['state_ms'],dict(RUNNING=2.,RUNNABLE=3.,BLOCKED=20.,UNKNOWN=0.))
        self.assertEqual(r['classification'],'BLOCKING_DOMINATED')

    def test_other_threads_do_not_change_target_state(self):
        events=[switch(0,2,1),switch(2,3,4,'R'),wake(3,4)]
        self.assertEqual(scheduler_window(events,1,1_000_000,5_000_000)['state_ms']['RUNNING'],4.)

    def test_missing_initial_state_stays_unknown(self):
        r=scheduler_window([switch(3,2,1)],1,1_000_000,5_000_000)
        self.assertEqual(r['state_ms']['UNKNOWN'],2.)
        self.assertFalse(r['coverage_complete'])

    def test_no_events_do_not_prove_cpu_execution(self):
        r=scheduler_window([],1,1,1_000_001)
        self.assertEqual(r['state_ms']['UNKNOWN'],1.)
        self.assertEqual(r['classification'],'INCOMPLETE_TRACE')

    def test_observation_pause_marks_incomplete(self):
        r=scheduler_window([switch(0,2,1)],1,1_000_000,5_000_000,[(2_000_000,3_000_000)])
        self.assertFalse(r['coverage_complete'])

    def test_pause_outside_window_does_not_hide_evidence(self):
        r=scheduler_window([switch(0,2,1)],1,1_000_000,5_000_000,[(6_000_000,7_000_000)])
        self.assertTrue(r['coverage_complete'])

    def test_running_thread_wakeup_does_not_stop_it(self):
        r=scheduler_window([switch(0,2,1),wake(2,1)],1,1_000_000,5_000_000)
        self.assertEqual(r['state_ms']['RUNNING'],4.)

    def test_bad_window_is_rejected(self):
        with self.assertRaises(ValueError):scheduler_window([],1,2,1)

    def test_parser_retains_preemption_and_exact_time(self):
        text=''' python3-44 [002] d..2. 100.123456: sched_switch: prev_comm=python3 prev_pid=44 prev_prio=120 prev_state=R+ ==> next_comm=worker next_pid=45 next_prio=120
 worker-45 [001] d..2. 100.123460: sched_wakeup: comm=python3 pid=44 prio=120 target_cpu=002
'''
        events=parse_scheduler_events(text)
        self.assertEqual(events[0]['mono_ns'],100123456000)
        self.assertEqual(events[0]['prev_state'],'R+')
        self.assertEqual(events[1]['tid'],44)

    def test_clipped_start_uses_prior_switch_state(self):
        r=scheduler_window([switch(0,1,2,'D'),wake(10,1),switch(20,2,1)],1,5_000_000,25_000_000)
        self.assertEqual(r['state_ms'],dict(RUNNING=5.,RUNNABLE=10.,BLOCKED=5.,UNKNOWN=0.))


class FaultCorrelationTests(unittest.TestCase):
    def setUp(self):
        self.report=dict(abi_version=2,task=1,start_ns=100,native_return_ns=150,
            release_decision_ns=160,after_unlock_ns=170,hardcap=1,guard=0,
            native_status=0,submitted=1,completed=1)

    def test_current_hardcap_is_matched(self):
        self.assertTrue(matching_fault_report(self.report,90,180))

    def test_stale_normal_report_is_not_a_fault(self):
        self.report['hardcap']=0
        self.assertFalse(matching_fault_report(self.report,90,180))

    def test_old_fault_from_previous_cooldown_is_rejected(self):
        self.assertFalse(matching_fault_report(self.report,200,300))

    def test_other_task_is_rejected(self):
        self.report['task']=2
        self.assertFalse(matching_fault_report(self.report,90,180))

    def test_future_or_inconsistent_report_is_rejected(self):
        self.report['after_unlock_ns']=181
        self.assertFalse(matching_fault_report(self.report,90,180))

    def test_native_failure_without_submission_is_not_execution_evidence(self):
        self.report.update(hardcap=0,native_status=-1,submitted=0,completed=0)
        self.assertFalse(matching_fault_report(self.report,90,180))


if __name__=='__main__':unittest.main()
