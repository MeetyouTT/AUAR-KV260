import unittest
from native_thread_discovery import event_rows,calls,identify


class DiscoveryTests(unittest.TestCase):
    def rows(self):
        return event_rows(''' python3-1399 [003] d.... 123.000001: native_entry: (address) runner=0x2
 python3-1400 [000] d.... 123.000002: native_entry: (address) runner=0x1
 python3-1400 [000] d.... 123.000003: native_exit: (address) ret=0
 python3-1399 [003] d.... 123.040000: native_exit: (address) ret=0
''')

    def test_integer_monotonic_nanoseconds(self):
        self.assertEqual(self.rows()[0]['mono_ns'],123000001000)

    def test_pairs_follow_thread_not_adjacent_entries(self):
        windows=calls(self.rows())
        self.assertEqual([(w['tid'],w['runner_id']) for w in windows],[(1400,1),(1399,2)])

    def test_native_report_identifies_its_enclosing_call(self):
        found=identify(self.rows(),[('yunet',dict(start_ns=123001000000,after_unlock_ns=123039000000))])
        self.assertEqual(found,dict(yunet=dict(tid=1399,runner_id=2)))

    def test_overlapping_candidates_do_not_guess(self):
        self.assertEqual(identify(self.rows(),[('yunet',dict(start_ns=123000002000,after_unlock_ns=123000003000))]),{})

    def test_zero_start_admission_denial_does_not_identify_a_thread(self):
        self.assertEqual(identify(self.rows(),[('yunet',dict(start_ns=0,after_unlock_ns=0))]),{})

    def test_incomplete_call_is_excluded(self):
        self.assertEqual(calls(self.rows()[:2]),[])


if __name__=='__main__':unittest.main()
