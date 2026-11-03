import hashlib
import json
from pathlib import Path
import unittest

import public_transducer_worker as worker


class Clock:
    def __init__(self):
        self.wall, self.cpu = 100.0, 0.0

    def now(self):
        return self.wall

    def cpu_now(self):
        return self.cpu

    def sleep(self, duration):
        self.wall += duration

    def work(self, duration):
        self.wall += duration
        self.cpu += duration


class Stream:
    def __init__(self):
        self.chunks, self.ready, self.finished = [], 0, False

    def accept_waveform(self, rate, samples):
        assert rate == 16000 and not self.finished
        self.chunks.append(list(samples))
        self.ready += 1

    def input_finished(self):
        self.finished = True
        self.ready += 1


class Recognizer:
    def __init__(self, clock, cost):
        self.clock, self.cost = clock, cost

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
        return "你好"


class WorkerChecks(unittest.TestCase):
    def test_pins_and_frozen_quality_validator_match(self):
        directory = Path(__file__).parent
        source = json.loads((directory / "official_files.json").read_text(encoding="utf-8"))
        self.assertEqual(source["revision"], worker.SOURCE_REVISION)
        self.assertEqual(source["export_configuration"]["decode_chunk_len"], 32)
        self.assertEqual({x["role"]: (x["filename"], x["bytes"], x["sha256"])
                          for x in source["files"]}, worker.FILES)
        helper_path = directory.parent / "quality" / "public_quality_worker.py"
        self.assertEqual(hashlib.sha256(helper_path.read_bytes()).hexdigest(), worker.HELPER_SHA)
        helper = worker.load_quality_helper(str(helper_path.resolve()))
        self.assertEqual(len(helper.CASES), 8)
        self.assertEqual(helper.TEXT_SET_SHA,
                         "e41dc194e00e3b76c40bdf4ee96cadf364e088a9c2c1f180ff872d6e77f72ede")

    def test_quality_and_paced_flush_preserve_samples_and_report_lag(self):
        samples = list(range(41760))
        for realtime, feed_ms, cost in ((False, 160, 0.001), (True, 20, 0.001),
                                        (True, 160, 0.001), (True, 20, 0.2)):
            with self.subTest(realtime=realtime, feed_ms=feed_ms, cost=cost):
                clock = Clock()
                recognizer = Recognizer(clock, cost)
                _, stats = worker.decode_round(
                    recognizer, samples, [0] * 10560, realtime=realtime,
                    feed_ms=feed_ms, deadline=1000, clock=clock.now,
                    cpu=clock.cpu_now, sleep=clock.sleep, monotonic=clock.now)
                self.assertEqual([v for chunk in recognizer.stream.chunks[:-1] for v in chunk], samples)
                self.assertEqual(recognizer.stream.chunks[-1], [0] * 10560)
                self.assertEqual(stats["tail_wait_ms"], 0)
                if not realtime:
                    self.assertIsNone(stats["final_after_scheduled_input_end_ms"])
                elif cost == 0.001:
                    self.assertLess(stats["final_after_scheduled_input_end_ms"], 10)
                else:
                    self.assertGreater(stats["feed_lateness_max_ms"], 20000)
                    self.assertGreater(stats["final_after_scheduled_input_end_ms"], 20000)
                    self.assertGreater(stats["unfed_elapsed_audio_peak_ms"], 2000)


if __name__ == "__main__":
    unittest.main()
