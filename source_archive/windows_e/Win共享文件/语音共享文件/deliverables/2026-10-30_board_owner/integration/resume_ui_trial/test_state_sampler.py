import importlib.util
from pathlib import Path
import json
import unittest


path = Path(__file__).with_name('read_only_state_sampler.py')
spec = importlib.util.spec_from_file_location('sanitized_ui_fixture', path)
sampler = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sampler)


class SanitizerTests(unittest.TestCase):
    def test_private_values_images_errors_and_unknown_strings_never_leave_filter(self):
        state = dict(reply='PRIVATE-CONVERSATION', identity=dict(person_id='PRIVATE-ID'),
                     preview='PRIVATE-IMAGE', error='PRIVATE-ERROR',
                     character_pair=dict(display_name='PRIVATE-NAME', state='PRIVATE-ENUM'),
                     local_transcription=dict(text='PRIVATE-ASR', service=dict(
                         voice_enrollment=dict(person_id='PRIVATE-ENROLL'), enabled=True)),
                     avatar_display=dict(frames=16, paint_at=1., visible=True))
        clean = sampler.sanitize(state)
        encoded = json.dumps(clean)
        self.assertNotIn('PRIVATE-', encoded)
        self.assertEqual(clean['character_pair.state'], 'OTHER')
        self.assertTrue(clean['error.present'])
        self.assertTrue(clean['local_transcription.service.enabled'])

    def test_present_null_is_distinguished_from_absent_mechanical_protection(self):
        clean = sampler.sanitize(dict(manual_pan=dict(state='FAULT', pulse_us=None,
                                                      target_us=None, automatic_following=False)))
        self.assertIn('manual_pan.pulse_us', clean)
        self.assertIsNone(clean['manual_pan.pulse_us'])
        self.assertNotIn('manual_pan.pulse_us', clean['missing_fields'])
        absent = sampler.sanitize({})
        self.assertIn('manual_pan.pulse_us', absent['missing_fields'])

    def test_native_fps_uses_only_visible_successful_swap_counters(self):
        def row(frames, at, visible=True):
            return {'state': {'avatar_display.frames':frames, 'avatar_display.paint_at':at,
                              'avatar_display.visible':visible,
                              'avatar_display.frame_scheduling_active':visible}}
        result = sampler.observed_fps([row(0, 10.), row(16, 11.), row(16, 20., False),
                                       row(16, 22., False), row(20, 23.), row(36, 24.)])
        self.assertEqual(result['visible_swap_fps'], 16.)
        self.assertEqual(result['visible_swap_frames'], 32)
        self.assertEqual(result['visible_swap_span_seconds'], 2.)


if __name__ == '__main__':
    unittest.main(verbosity=2)
