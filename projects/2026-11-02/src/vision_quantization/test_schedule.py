import unittest
from dpu_vision_schedule import DpuVisionSchedule


class ScheduleTests(unittest.TestCase):
    def test_secondary_waits_for_primary_deadline(self):
        now = [1.]
        schedule = DpuVisionSchedule(clock=lambda: now[0])
        with schedule.optional('yunet') as acquired:
            self.assertFalse(acquired)
        with schedule.primary(1.1):
            with schedule.optional('yunet') as acquired:
                self.assertFalse(acquired)
        with schedule.optional('yunet') as acquired:
            self.assertTrue(acquired)
            now[0] += .004
        self.assertEqual(schedule.health()['optional']['yunet']['calls'], 1)

    def test_short_gap_and_waiting_primary_deny_job(self):
        schedule = DpuVisionSchedule(clock=lambda: 1.)
        schedule.next_primary = 1.02
        with schedule.optional('yunet') as acquired:
            self.assertFalse(acquired)
        schedule.next_primary, schedule.waiting_primary = 1.1, 1
        with schedule.optional('sface') as acquired:
            self.assertFalse(acquired)

    def test_overrun_disables_only_that_optional_task_and_releases_owner(self):
        now = [1.]
        schedule = DpuVisionSchedule(clock=lambda: now[0])
        schedule.next_primary = 1.2
        with schedule.optional('yunet') as acquired:
            self.assertTrue(acquired)
            now[0] += .031
        self.assertTrue(schedule.disabled('yunet'))
        with schedule.optional('sface') as acquired:
            self.assertTrue(acquired)
        with schedule.primary(1.3):
            pass
        self.assertIsNone(schedule.health()['active'])

    def test_measured_2065_ms_with_room_before_yolo_is_not_a_deadline_failure(self):
        now = [1.]
        schedule = DpuVisionSchedule(clock=lambda: now[0])
        schedule.next_primary = 1.1
        with schedule.optional('yunet') as acquired:
            self.assertTrue(acquired)
            now[0] += .02065
        self.assertFalse(schedule.disabled('yunet'))
        stats = schedule.health()['optional']['yunet']
        self.assertEqual(stats['budget_exceeded'], 1)
        self.assertEqual(stats['overruns'], 0)
        self.assertAlmostEqual(stats['estimated_budget_ms'], 22.65)

    def test_crossing_reserved_primary_guard_disables_the_task(self):
        now = [1.]
        schedule = DpuVisionSchedule(clock=lambda: now[0])
        schedule.next_primary = 1.026
        with schedule.optional('yunet') as acquired:
            self.assertTrue(acquired)
            now[0] += .022
        self.assertTrue(schedule.disabled('yunet'))

    def test_failed_job_releases_primary(self):
        schedule = DpuVisionSchedule(clock=lambda: 1.)
        schedule.next_primary = 2.
        with self.assertRaises(RuntimeError):
            with schedule.optional('yunet') as acquired:
                self.assertTrue(acquired)
                raise RuntimeError('simulated VART error')
        with schedule.primary(2.):
            pass
        self.assertEqual(schedule.health()['primary_calls'], 1)


if __name__ == '__main__':
    unittest.main()
