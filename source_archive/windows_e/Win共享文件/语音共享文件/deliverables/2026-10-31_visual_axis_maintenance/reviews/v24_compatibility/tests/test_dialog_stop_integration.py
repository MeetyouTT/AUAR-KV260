"""Exercise the real composed stage methods with lightweight widget doubles."""
from types import SimpleNamespace
import unittest
from tools.face_pan_controls import stage_type


class Widget:
    def __init__(self):
        self.sensitive = None
        self.text = None
        self.active = None

    def set_sensitive(self, value):
        self.sensitive = value

    def set_text(self, value):
        self.text = value

    def set_tooltip_text(self, value):
        pass

    def set_active(self, value):
        self.active = value


def dialog(*, running):
    cls = stage_type(object, lambda: None)
    stage = cls.__new__(cls)
    stage.pan_dialog = object()
    value = dict(state='UNAVAILABLE', pulse_us=None, automatic_following=running,
        minimum_us=500, maximum_us=2500, left_sign=-1, message='', error='')
    stage.pan = SimpleNamespace(running=running, read=lambda: dict(value))
    stage.pan_step_us = 20
    stage.pan_buttons = {k: Widget() for k in ('left', 'right', 'stop')}
    stage.pan_position = Widget()
    stage.pan_message = Widget()
    stage.pan_step = Widget()
    stage.pan_reconnect = Widget()
    stage.pan_reverse = Widget()
    stage.pan_updating = False
    return stage


class DialogStopIntegrationTests(unittest.TestCase):
    def test_stale_follow_report_keeps_dedicated_stop_available(self):
        stage = dialog(running=True)
        stage.refresh_pan_dialog()
        self.assertTrue(stage.pan_buttons['stop'].sensitive)
        self.assertFalse(stage.pan_buttons['left'].sensitive)
        self.assertFalse(stage.pan_buttons['right'].sensitive)
        self.assertFalse(stage.pan_reconnect.sensitive)

    def test_unavailable_manual_backend_keeps_existing_reconnect_policy(self):
        stage = dialog(running=False)
        stage.refresh_pan_dialog()
        self.assertFalse(stage.pan_buttons['stop'].sensitive)
        self.assertTrue(stage.pan_reconnect.sensitive)


if __name__ == '__main__':
    unittest.main()
