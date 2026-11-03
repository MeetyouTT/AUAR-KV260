"""Timing/flush checks only; no inference package, model, audio device, or files."""
import hashlib
import unittest

from public_streaming_probe import (PUBLIC_WAV_SAMPLES, SAMPLE_RATE,
                                    TAIL_SAMPLES, run_round)


class Clock:
    def __init__(self):
        self.wall = 100.0
        self.cpu = 0.0
        self.sleeps = []

    def now(self):
        return self.wall

    def cpu_now(self):
        return self.cpu

    def sleep(self, duration):
        self.sleeps.append(duration)
        self.wall += duration

    def work(self, duration):
        self.wall += duration
        self.cpu += duration


class Stream:
    def __init__(self):
        self.chunks = []
        self.ready = 0
        self.finished = False
        self.finish_chunk_count = None

    def accept_waveform(self, rate, samples):
        assert rate == SAMPLE_RATE and not self.finished
        self.chunks.append(list(samples))
        self.ready += 1

    def input_finished(self):
        self.finished = True
        self.finish_chunk_count = len(self.chunks)
        self.ready += 1


class Recognizer:
    def __init__(self, clock, cost):
        self.clock, self.cost = clock, cost
        self.stream = None

    def create_stream(self):
        self.stream = Stream()
        return self.stream

    def is_ready(self, stream):
        return stream.ready > 0

    def decode_stream(self, stream):
        self.clock.work(self.cost)
        stream.ready -= 1

    def get_result(self, stream):
        assert stream.finished and stream.ready == 0
        return "测试123。"


class ProbeTimingTests(unittest.TestCase):
    def test_partial_tail_order_and_no_zero_realtime_wait(self):
        samples = list(range(PUBLIC_WAV_SAMPLES))
        for feed_ms in (20, 160):
            with self.subTest(feed_ms=feed_ms):
                clock = Clock()
                recognizer = Recognizer(clock, 0.001)
                result, text = run_round(
                    recognizer, samples, [0] * TAIL_SAMPLES, feed_ms, "测试123",
                    clock=clock.now, sleep=clock.sleep, cpu=clock.cpu_now)
                chunks = recognizer.stream.chunks
                self.assertEqual([item for chunk in chunks[:-1] for item in chunk], samples)
                self.assertEqual(chunks[-1], [0] * TAIL_SAMPLES)
                self.assertEqual(recognizer.stream.finish_chunk_count, len(chunks))
                self.assertEqual(result["last_real_chunk_samples"], 234)
                self.assertEqual(result["tail_wait_ms"], 0)
                self.assertLess(result["final_after_scheduled_input_end_ms"], 10)
                self.assertTrue(result["accuracy"]["normalized_exact"])
                self.assertEqual(text, "测试123")

    def test_slow_consumer_reports_backlog_without_inventing_gold(self):
        clock = Clock()
        recognizer = Recognizer(clock, 0.2)
        result, _ = run_round(
            recognizer, [1] * PUBLIC_WAV_SAMPLES, [0] * TAIL_SAMPLES, 20,
            clock=clock.now, sleep=clock.sleep, cpu=clock.cpu_now)
        self.assertGreater(result["feed_lateness_max_ms"], 50000)
        self.assertGreater(result["unfed_elapsed_audio_peak_ms"], 4000)
        self.assertGreater(result["final_after_scheduled_input_end_ms"], 50000)
        self.assertAlmostEqual(result["final_after_last_real_accept_ms"], 600, places=2)
        self.assertIsNone(result["accuracy"])
        self.assertFalse(result["gold_reference_supplied"])
        self.assertEqual(result["public_result_sha256"],
                         hashlib.sha256("测试123。".encode()).hexdigest())
        self.assertNotIn("测试", str(result))


if __name__ == "__main__":
    unittest.main()
