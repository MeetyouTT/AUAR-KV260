"""Synthetic checks: no connection, live state, text, audio or device access."""
import contextlib
import importlib.util
import io
import json
from pathlib import Path
import unittest


HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('local_ui_stage_collector', HERE/'collect_ui_stage_metadata.py')
collector = importlib.util.module_from_spec(spec)
spec.loader.exec_module(collector)


class WhitelistTests(unittest.TestCase):
    def collect(self, state):
        out = dict(observed_mono=1., startup_sha256='0'*64, phase='IDLE', playing=False,
            listening={}, native={}, runtime_faults={}, audio_output={}, safe_capture={})
        capture = io.StringIO()
        with contextlib.redirect_stdout(capture):
            exec(collector.REMOTE_EXTRA, dict(state=state, out=out, json=json))
        return json.loads(capture.getvalue())

    def test_retains_all_seven_stage_numbers(self):
        stages = dict(commands=1.,controller_read=2.,settings=3.,runtime_widgets=4.,
            business_widgets=5.,presentation=6.,business_public=500.)
        result = self.collect(dict(ui_tick_ms=521.,ui_stage_timings_ms=stages))
        self.assertEqual(stages, result['ui_stage_timings_ms'])
        self.assertEqual(521., result['ui_tick_ms'])

    def test_retains_nested_profile_quantiles(self):
        profile = dict(frames=240,window_seconds=15.,
            **{key:dict(p50=1.,p95=2.,max=3.) for key in
               ('core','compose_resize','jpeg','public','total','interval')})
        result = self.collect(dict(avatar_renderer=dict(profile=profile)))
        self.assertEqual(profile, result['renderer_profile'])

    def test_private_and_unexpected_fields_never_export(self):
        sentinel = 'PRIVATE_SYNTHETIC_BODY_MUST_NOT_APPEAR'
        result = self.collect(dict(reply=sentinel,ui_stage_timings_ms=dict(error=sentinel,commands=1),
            avatar_renderer=dict(profile=dict(text=sentinel,core=dict(p50=2,error=sentinel,body=sentinel)),
                timings_ms=dict(reply=sentinel,total=3)), runtime_faults=dict(text=sentinel)))
        self.assertNotIn(sentinel, json.dumps(result))
        self.assertEqual(dict(commands=1), result['ui_stage_timings_ms'])
        self.assertEqual(dict(core=dict(p50=2)), result['renderer_profile'])
        self.assertEqual(dict(total=3), result['renderer_timings_ms'])

    def test_invalid_number_types_and_nonfinite_values_rejected(self):
        result = self.collect(dict(ui_tick_ms=float('nan'),ui_stage_timings_ms=dict(
            commands=True,controller_read=float('inf'),settings=-1,runtime_widgets='500',
            business_widgets=None,presentation=[],business_public=9007199254740992)))
        self.assertNotIn('ui_tick_ms', result)
        self.assertEqual({}, result['ui_stage_timings_ms'])

    def test_wrong_container_shapes_are_empty(self):
        result = self.collect(dict(ui_stage_timings_ms='wrong',avatar_renderer=['wrong']))
        for key in ('ui_stage_timings_ms','renderer_profile','renderer_timings_ms'):
            self.assertEqual({}, result[key])

    def test_new_widget_and_completed_callback_fields_are_whitelisted(self):
        sentinel='PRIVATE_SYNTHETIC_BODY_MUST_NOT_APPEAR'
        result=self.collect(dict(ui_runtime_timings_ms=dict(display_activity=502.,thread_cpu=10.,text=sentinel),
            ui_settings_timings_ms=dict(device_scan=100.,widgets=20.,error=sentinel),
            ui_widget_writes=dict(applied=6,skipped=48,body=sentinel),
            ui_callback_previous=dict(sequence=1,wall_ms=600.,publish_ms=50.,succeeded=True,
                completed_mono=float('inf'),text=sentinel)))
        self.assertNotIn(sentinel,json.dumps(result))
        self.assertEqual(dict(display_activity=502.,thread_cpu=10.),result['ui_runtime_timings_ms'])
        self.assertEqual(dict(device_scan=100.,widgets=20.),result['ui_settings_timings_ms'])
        self.assertEqual(dict(applied=6,skipped=48),result['ui_widget_writes'])
        self.assertEqual(dict(sequence=1,wall_ms=600.,publish_ms=50.,succeeded=True),result['ui_callback_previous'])


if __name__ == '__main__':
    unittest.main(verbosity=2)
