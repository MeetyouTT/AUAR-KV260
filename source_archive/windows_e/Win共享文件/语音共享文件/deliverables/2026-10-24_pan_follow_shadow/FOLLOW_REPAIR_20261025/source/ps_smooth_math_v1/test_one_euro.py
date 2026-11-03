import math
import random
import statistics
import unittest

from one_euro import OneEuroFilter


class OneEuroTests(unittest.TestCase):
    def test_first_sample_and_constant_are_exact(self):
        f = OneEuroFilter()
        for timestamp in (0., .08, .135, .25, .45):
            self.assertEqual(f(.6, timestamp), .6)
        self.assertEqual(f.derivative_ratio_s, 0.)

    def test_formula_matches_pinned_cpp_last_filtered_derivative(self):
        f = OneEuroFilter(min_cutoff_hz=.8, beta=6., derivative_cutoff_hz=1.)
        filtered, derivative, previous = .5, 0., 1.
        self.assertEqual(f(.5, 1.), .5)
        for timestamp, value in ((1.08, .52), (1.135, .6), (1.255, .65), (1.32, .61)):
            dt = timestamp-previous
            alpha_d = 2*math.pi*dt/(1+2*math.pi*dt)
            derivative = alpha_d*(value-filtered)/dt+(1-alpha_d)*derivative
            cutoff = .8+6*abs(derivative)
            alpha_x = 2*math.pi*cutoff*dt/(1+2*math.pi*cutoff*dt)
            filtered = alpha_x*value+(1-alpha_x)*filtered
            self.assertAlmostEqual(f(value, timestamp), filtered, places=14)
            self.assertAlmostEqual(f.derivative_ratio_s, derivative, places=14)
            previous = timestamp

    def test_actual_intervals_change_response(self):
        short, long = OneEuroFilter(beta=0), OneEuroFilter(beta=0)
        short(.5, 0.);long(.5, 0.)
        self.assertGreater(long(.7, .12), short(.7, .04))

    def test_duplicate_old_or_invalid_samples_cannot_mutate_state(self):
        f = OneEuroFilter();f(.5, 1.);before = dict(f.__dict__)
        for value, timestamp in ((.6, 1.), (.6, .9), (float('nan'), 2.), (.6, float('inf')), (True, 2.)):
            with self.assertRaises(ValueError):
                f(value, timestamp)
            self.assertEqual(f.__dict__, before)

    def test_invalid_parameters_are_rejected(self):
        for kwargs in ({'beta': -1}, {'min_cutoff_hz': 0}, {'derivative_cutoff_hz': 0}, {'beta': float('inf')}):
            with self.assertRaises(ValueError):
                OneEuroFilter(**kwargs)

    def test_beta_zero_is_one_lowpass_without_hidden_median_or_extra_ema(self):
        f = OneEuroFilter(min_cutoff_hz=1., beta=0.)
        self.assertEqual(f(.5, 0.), .5)
        alpha = 2*math.pi*.08/(1+2*math.pi*.08)
        self.assertAlmostEqual(f(.8, .08), alpha*.8+(1-alpha)*.5, places=14)

    def test_adaptation_reduces_monotonic_fast_motion_lag(self):
        fixed, adaptive = OneEuroFilter(beta=0.), OneEuroFilter(beta=6.)
        errors_fixed, errors_adaptive = [], []
        for i in range(30):
            time = i*.08;value = .3+min(time*.25, .6)
            errors_fixed.append(abs(fixed(value, time)-value))
            errors_adaptive.append(abs(adaptive(value, time)-value))
        self.assertLess(sum(errors_adaptive), sum(errors_fixed)*.6)

    def test_stationary_noise_is_reduced(self):
        rng = random.Random(3);f = OneEuroFilter();raw, output = [], []
        for i in range(300):
            value = .5+rng.gauss(0, .002)
            filtered = f(value, i*.08)
            if i > 40:raw.append(value);output.append(filtered)
        self.assertLess(statistics.pstdev(output), statistics.pstdev(raw)*.7)

    def test_no_extrapolation_or_overshoot(self):
        f = OneEuroFilter();previous = f(.5, 0.)
        for i, value in enumerate((.55, .8, .7, .3, .4, .5), 1):
            result = f(value, i*.08)
            self.assertGreaterEqual(result, min(previous, value))
            self.assertLessEqual(result, max(previous, value))
            previous = result

    def test_context_reset_drops_previous_position_velocity_and_time(self):
        f = OneEuroFilter();f(.2, 1.);f(.8, 1.08);f.reset()
        self.assertEqual(f(.4, .5), .4)
        self.assertEqual(f.derivative_ratio_s, 0.)

    def test_one_euro_alone_must_not_be_treated_as_spike_rejection(self):
        f = OneEuroFilter()
        for i in range(20):f(.5, i*.08)
        self.assertGreater(f(.75, 20*.08)-.5, .1)


if __name__ == '__main__':
    unittest.main()
