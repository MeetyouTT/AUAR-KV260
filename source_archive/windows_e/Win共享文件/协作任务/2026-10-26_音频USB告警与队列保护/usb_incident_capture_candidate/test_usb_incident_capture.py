"""Offline provenance, owner-loss, bounded evidence and trigger behavior."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import usb_incident_capture as capture

BOOT = '16a07283-9e14-45e6-816d-3bda4cf333a7'


def entry(stamp, **changes):
    row = dict(_BOOT_ID=BOOT.replace('-', ''), _TRANSPORT='kernel',
               __MONOTONIC_TIMESTAMP=str(stamp), MESSAGE=capture.WARNING)
    row.update(changes)
    return json.dumps(row)


class Clock:
    def __init__(self):
        self.now = 1000.
    def __call__(self):
        return self.now
    def sleep(self, seconds):
        if seconds < 0:
            raise AssertionError('Negative sleep')
        self.now += seconds


class FakePlatform:
    boot = BOOT.replace('-', '')
    def __init__(self, clock, events=(), check_error_at=None, journal_error=False):
        self.clock, self.events, self.check_error_at = clock, events, check_error_at
        self.journal_error = journal_error
        self.check_calls = self.captures = self.journal_calls = 0
    def check(self):
        self.check_calls += 1
        if self.check_error_at is not None and self.clock() >= self.check_error_at:
            raise capture.CaptureError('RUNTIME_OWNER_CHANGED')
        return dict(camera_pid=720342, gui_pid=772087, flags=0, width_us=1402,
                    automatic_following=False, audio_owner_pid=772163)
    def journal(self):
        self.journal_calls += 1
        if self.journal_error:
            raise OSError('readonly journal failed')
        return '\n'.join(entry(round(t * 1e6)) for t in self.events if t <= self.clock())
    def capture(self, clock, sleep, end):
        self.captures += 1
        self.check()
        sleep(3)
        self.check()
        return dict(raw_pointer_delta=dict(hw_ptr=144000, appl_ptr=144000),
                    USB_root_cause_proven=False)


class IncidentTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)

    def output(self, name='run'):
        result = capture.BoundedOutput(Path(self.temp.name) / name)
        self.addCleanup(result.close)
        return result

    def test_boot_kernel_slot_source_and_monotonic_microseconds_are_strict(self):
        gate = capture.JournalGate(BOOT, 1000000)
        lines = [entry(999999), entry(1000000), entry(1000001), entry(1000001),
                 entry(1000002, _BOOT_ID='0' * 32), entry(1000003, _TRANSPORT='stdout'),
                 entry(1000004, MESSAGE=capture.WARNING.replace('slot 4', 'slot 5')),
                 entry(1000005, MESSAGE=capture.WARNING + ' unrelated'), entry(2000000)]
        result = gate.consume('\n'.join(lines), 1100000)
        self.assertEqual(result['new_warning_timestamps_us'], [1000001])
        self.assertEqual(result['filtered'], dict(other_boot=1, other_message=3,
                                                historical_or_duplicate=3, future=1))
        repeated = gate.consume(entry(1000001) + '\n' + entry(1000006), 1100000)
        self.assertEqual(repeated['new_warning_timestamps_us'], [1000006])
        self.assertEqual(gate.last_us, 1000006)

    def test_capped_journal_is_labeled_and_bad_payload_stops(self):
        gate = capture.JournalGate(BOOT, 0)
        lines = '\n'.join(entry(i) for i in range(1, 121))
        self.assertTrue(gate.consume(lines, 200)['sample_capped'])
        for raw in (lines + '\n' + entry(121), '{bad}', entry(2, __MONOTONIC_TIMESTAMP='2.3')):
            with self.assertRaises(capture.CaptureError):
                gate.consume(raw, 200)

    def test_three_distinct_incidents_then_exit_without_service_actions(self):
        clock = Clock()
        platform = FakePlatform(clock, events=(999., 1001., 1002., 1015., 1071., 1141.))
        output = self.output()
        result = capture.run(platform, output, 300, clock, clock.sleep)
        self.assertEqual(result['reason'], 'MAX_INCIDENTS_RECORDED')
        self.assertEqual(result['incidents'], 3)
        self.assertEqual(platform.captures, 3)
        self.assertFalse(result['automatic_recovery'])
        self.assertEqual(result['motor_commands'], 0)
        self.assertLessEqual(result['elapsed_s'], 300)
        files = sorted(output.path.glob('incident-*.json'))
        self.assertEqual(len(files), 3)
        times = [json.loads(p.read_text())['elapsed_s'] for p in files]
        self.assertTrue(all(b-a >= 60 for a,b in zip(times,times[1:])))
        self.assertEqual(result['new_warning_timestamps'], 5)

    def test_duplicate_and_cooldown_events_do_not_trigger_later(self):
        clock = Clock()
        platform = FakePlatform(clock, events=(1001., 1015.))
        output = self.output()
        result = capture.run(platform, output, 150, clock, clock.sleep)
        self.assertEqual(result['incidents'], 1)
        self.assertEqual(result['new_warning_timestamps'], 2)
        self.assertEqual(result['elapsed_s'], 150)
        self.assertEqual(result['polls'], 15)

    def test_owner_change_stops_instead_of_touching_new_owner(self):
        clock = Clock()
        platform = FakePlatform(clock, events=(1001.,), check_error_at=1020.)
        output = self.output()
        result = capture.run(platform, output, 60, clock, clock.sleep)
        self.assertEqual(result['reason'], 'CAPTURE_STOPPED_ON_ERROR')
        self.assertIn('RUNTIME_OWNER_CHANGED', result['error'])
        self.assertEqual(result['elapsed_s'], 20)
        self.assertEqual(platform.captures, 1)

    def test_owner_change_during_capture_keeps_no_completed_incident(self):
        clock = Clock()
        platform = FakePlatform(clock, events=(1001.,), check_error_at=1012.)
        output = self.output()
        result = capture.run(platform, output, 60, clock, clock.sleep)
        self.assertEqual(result['incidents'], 0)
        self.assertIn('RUNTIME_OWNER_CHANGED', result['error'])
        self.assertEqual(list(output.path.glob('incident-*.json')), [])
        self.assertIn('"incident_triggered":true', (output.path/'progress.jsonl').read_text())

    def test_read_fault_stops_at_first_fault_and_final_is_written(self):
        clock = Clock()
        platform = FakePlatform(clock, journal_error=True)
        output = self.output()
        result = capture.run(platform, output, 7200, clock, clock.sleep)
        self.assertEqual(platform.journal_calls, 1)
        self.assertEqual(platform.captures, 0)
        self.assertEqual(result['elapsed_s'], 0)
        self.assertIn('readonly journal failed', result['error'])
        self.assertEqual(json.loads((output.path/'result.json').read_text()), result)

    def test_twenty_second_validation_has_two_polls_and_no_incident(self):
        clock = Clock()
        platform = FakePlatform(clock)
        output = self.output()
        result = capture.run(platform, output, 20, clock, clock.sleep)
        self.assertEqual((result['polls'], result['incidents'], result['elapsed_s']), (2, 0, 20))
        self.assertEqual(result['reason'], 'DURATION_ENDED')
        for invalid in (0, 7201):
            with self.assertRaises(ValueError):
                capture.run(platform, output, invalid, clock, clock.sleep)

    def test_existing_directory_and_symlink_are_not_reused(self):
        root = Path(self.temp.name)
        (root/'existing').mkdir()
        with self.assertRaises(FileExistsError):
            capture.BoundedOutput(root/'existing')
        (root/'linked').symlink_to(root/'existing', target_is_directory=True)
        with self.assertRaises(FileExistsError):
            capture.BoundedOutput(root/'linked')

    def test_evidence_exclusive_and_byte_limits_leave_final_reserve(self):
        output = self.output()
        output.write('incident-001.json', {'first': 1})
        with self.assertRaises(FileExistsError):
            output.write('incident-001.json', {'replacement': 2})
        self.assertEqual(json.loads((output.path/'incident-001.json').read_text()), {'first': 1})
        with self.assertRaises(capture.CaptureError):
            output.write('../outside.json', {})
        with self.assertRaises(capture.CaptureError):
            output.write('large.json', {'blob':'x' * capture.MAX_INCIDENT_BYTES})
        with self.assertRaises(capture.CaptureError):
            output.progress({'huge': 'x' * 4096})
        output.total = capture.MAX_TOTAL_BYTES - 8192
        with self.assertRaises(capture.CaptureError):
            output.progress({'blocked': True})
        output.write('result.json', {'reason':'BYTE_BOUND'}, limit=8192)
        self.assertLess(output.total, capture.MAX_TOTAL_BYTES)

    def test_pcm_parser_records_numbers_and_rejects_closed_or_bad_data(self):
        raw = 'state: RUNNING\nowner_pid: 42\nhw_ptr: 1000\nappl_ptr: 1008\ndelay: -1\navail: 0\nsecret: ignored\n'
        parsed = capture.pcm_fields(raw)
        self.assertEqual(parsed['delay'], -1)
        self.assertNotIn('secret', parsed)
        for invalid in ('closed\n', raw.replace('RUNNING','XRUN'), raw.replace('hw_ptr: 1000','hw_ptr: invalid')):
            with self.assertRaises(capture.CaptureError):
                capture.pcm_fields(invalid)

    def test_metadata_command_whitelist_rejects_control_before_spawning(self):
        with patch.object(capture.subprocess, 'Popen', side_effect=AssertionError('Must not spawn')):
            for command in (['usbreset','anything'], ['systemctl','restart','aura-avatar-ui.service'],
                            ['journalctl','--vacuum-size=1M']):
                with self.assertRaises(capture.CaptureError):
                    capture.command(command, 1024)

    def test_real_platform_owner_check_discards_private_http_content(self):
        boot = BOOT.replace('-', '')
        stat = '42 (private name) ' + ' '.join(['S'] + ['0'] * 18 + ['1234'] + ['0'] * 3)
        pcm = 'state: RUNNING\nowner_pid: 55\nhw_ptr: 1000\nappl_ptr: 1100\n'
        files = {'/proc/sys/kernel/random/boot_id':BOOT,
                 '/proc/42/stat':stat, '/proc/43/stat':stat,
                 '/proc/asound/card1/usbid':'17ef:a03b', capture.USB+'/idVendor':'17ef',
                 capture.USB+'/idProduct':'a03b', capture.SLOT+'/name':'1-1.2', capture.PCM+'/status':pcm}
        health = dict(pid=42, dpu_schedule=dict(primary_period_overruns=29, owner_fenced=False),
                      identity={'name':'private identity'})
        ui = dict(phase='IDLE', audio_output_state='IDLE_READY', reply='private reply',
                  manual_pan=dict(automatic_following=False, readback=dict(flags=0,width_us=1402,lease_left_ms=0)))
        with patch.object(capture.Platform, 'read', side_effect=lambda path, *a:files[path]), \
             patch.object(capture.Platform, 'get', side_effect=lambda port, path:health if port==8790 else ui), \
             patch.object(capture, 'command', return_value='43\n'):
            platform = capture.Platform(42,43)
            result = platform.check()
            self.assertEqual(platform.boot, boot)
            self.assertEqual(result['process_birth_ticks'], [1234,1234])
            self.assertNotIn('private', json.dumps(result))
            files['/proc/43/stat'] = stat.replace('1234','5678')
            with self.assertRaisesRegex(capture.CaptureError,'PID_REUSED'):
                platform.check()

    def test_incident_does_not_start_without_complete_three_second_window(self):
        clock = Clock()
        platform = FakePlatform(clock, events=(1001.,))
        output = self.output()
        result = capture.run(platform,output,12,clock,clock.sleep)
        self.assertEqual(platform.captures,0)
        self.assertEqual(result['incidents'],0)
        self.assertIn('INSUFFICIENT_TIME_FOR_INCIDENT',result['error'])

    def test_duration_7200_stays_within_progress_and_total_evidence_budget(self):
        clock = Clock()
        output = self.output()
        result = capture.run(FakePlatform(clock), output, 7200, clock, clock.sleep)
        self.assertEqual(result['polls'], 720)
        self.assertEqual(result['elapsed_s'], 7200)
        self.assertLess(output.progress_bytes, capture.MAX_PROGRESS_BYTES)
        self.assertLess(output.total, capture.MAX_TOTAL_BYTES)


if __name__ == '__main__':
    unittest.main()
