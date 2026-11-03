import unittest
from plan_fixed import LIMITS, TICK_S, make_plan, metrics


class FixedPlanTests(unittest.TestCase):
    def test_both_legs_finish_at_exact_endpoints_and_rest(self):
        for direction in (-1, 1):
            rows = make_plan(1420, direction)
            for index, position in ((0, 1420), (50, 1420 + 5 * direction), (100, 1420)):
                self.assertAlmostEqual(rows[index]['position_us'], position, places=7)
                self.assertAlmostEqual(rows[index]['velocity_us_s'], 0., places=7)
                self.assertAlmostEqual(rows[index]['acceleration_us_s2'], 0., places=7)

    def test_continuous_limits_and_sampled_jerk_hold_across_reversal(self):
        rows = make_plan(1420)
        for row in rows:
            self.assertLessEqual(abs(row['velocity_us_s']), LIMITS['speed_us_s'] + 1e-7)
            self.assertLessEqual(abs(row['acceleration_us_s2']), LIMITS['acceleration_us_s2'] + 1e-7)
        for a, b in zip(rows, rows[1:]):
            self.assertLessEqual(abs(b['acceleration_us_s2'] - a['acceleration_us_s2']) / TICK_S,
                                 LIMITS['jerk_us_s3'] + 1e-7)

    def test_integer_targets_never_overshoot_or_jump_more_than_one_us(self):
        for direction in (-1, 1):
            rows = make_plan(1420, direction)
            limits = sorted((1420, 1420 + 5 * direction))
            for row in rows:
                self.assertTrue(limits[0] <= row['target_us'] <= limits[1])
                self.assertTrue(limits[0] - 1e-7 <= row['position_us'] <= limits[1] + 1e-7)
            self.assertEqual(metrics(rows)['maximum_target_step_us'], 1)

    def test_reverse_direction_is_symmetric(self):
        forward, reverse = make_plan(1420, 1), make_plan(1420, -1)
        for a, b in zip(forward, reverse):
            self.assertAlmostEqual(a['position_us'] + b['position_us'], 2840., places=7)
            self.assertAlmostEqual(a['velocity_us_s'] + b['velocity_us_s'], 0., places=7)
            self.assertAlmostEqual(a['acceleration_us_s2'] + b['acceleration_us_s2'], 0., places=7)

    def test_translation_does_not_change_trajectory(self):
        a, b = make_plan(1420), make_plan(1500)
        for x, y in zip(a, b):
            self.assertAlmostEqual(y['position_us'] - x['position_us'], 80., places=7)
            self.assertAlmostEqual(y['velocity_us_s'], x['velocity_us_s'], places=7)

    def test_invalid_references_and_out_of_range_path_are_rejected(self):
        for reference, direction in ((1399, 1), (1601, -1), (1596, 1), (1404, -1), (True, 1), (1420., 1), (1420, 0)):
            with self.assertRaises(ValueError):
                make_plan(reference, direction)

    def test_first_quantized_change_does_not_claim_zero_startup_delay(self):
        result = metrics(make_plan(1420))
        # Independent jerk-only lower bound: p = j*t^3/6 until acceleration cap.
        self.assertGreater(result['first_changed_target_ms'], 150)
        self.assertEqual(result['first_changed_target_ms'], 160)
        self.assertEqual(result['target_changes'], 10)
        self.assertEqual(result['samples'], 101)

    def test_all_requested_samples_have_exact_20ms_timing(self):
        rows = make_plan(1420)
        self.assertEqual([r['time_ms'] for r in rows], list(range(0, 2001, 20)))


if __name__ == '__main__':
    unittest.main()
