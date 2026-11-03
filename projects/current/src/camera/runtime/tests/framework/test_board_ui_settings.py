import json
from pathlib import Path
import tempfile
import threading
import time
import types
import unittest

from tools.board_ui_settings import AlsaMixer, MixerService, SettingsStore, validate


def wait_for(predicate):
    deadline = time.monotonic()+3
    while time.monotonic() < deadline:
        if predicate():
            return
        time.sleep(.01)
    raise AssertionError('Mixer did not settle')


class FakeMixer:
    def __init__(self):
        self.actual = {'volume':100,'muted':False}
        self.requests = []
        self.fail = False

    def read(self):
        if self.fail:
            raise RuntimeError('device absent')
        return dict(self.actual)

    def apply(self, values):
        self.read()
        self.requests.append(dict(values))
        self.actual.update(values)
        return self.read()


class BoardUiSettingsTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name)/'preferences.json'
        self.store = SettingsStore(self.path)

    def service(self, backend):
        result = MixerService(self.store,backend,poll_seconds=.03)
        self.addCleanup(result.close)
        return result

    def test_preferences_persist_and_reload(self):
        self.store.update({'volume':73,'muted':True,'fullscreen':False})
        loaded = SettingsStore(self.path)
        self.assertTrue(loaded.loaded)
        self.assertEqual(loaded.read()['volume'],73)
        self.assertTrue(loaded.read()['muted'])
        self.assertFalse(loaded.read()['fullscreen'])

    def test_invalid_file_is_reported_without_overwrite(self):
        original = '{bad json'
        self.path.write_text(original)
        loaded = SettingsStore(self.path)
        self.assertFalse(loaded.loaded)
        self.assertTrue(loaded.load_error)
        self.assertEqual(self.path.read_text(),original)

    def test_invalid_and_unknown_settings_rejected(self):
        for values in ({'volume':True},{'volume':101},{'volume':-1},
                       {'volume':3.5},{'muted':1},{'firmware':'other'}):
            with self.subTest(values=values),self.assertRaises(ValueError):
                validate(values)

    def test_actual_alsa_output_parses_volume_and_mute(self):
        output = 'Mono: Playback 151 [100%] [-0.06dB] [on]'
        self.assertEqual(AlsaMixer.parse(output),{'volume':100,'muted':False})
        self.assertTrue(AlsaMixer.parse(output.replace('[on]','[off]'))['muted'])

    def test_ambiguous_alsa_output_is_not_treated_as_success(self):
        with self.assertRaises(RuntimeError):
            AlsaMixer.parse('Left: Playback 20 [10%] [on]\nRight: Playback 80 [60%] [on]')

    def test_only_pcm_playback_is_written_and_read_back(self):
        calls=[]
        def run(args,**kwargs):
            calls.append(args)
            volume=100 if len(calls)==1 else 60
            return types.SimpleNamespace(returncode=0,stdout=f'Mono: Playback 90 [{volume}%] [on]')
        actual=AlsaMixer(run).apply({'volume':60})
        self.assertEqual(actual['volume'],60)
        self.assertEqual(calls[1],['amixer','-c','MCP01','sset','PCM','60%','unmute'])
        self.assertEqual(calls[2],['amixer','-c','MCP01','sget','PCM'])

    def test_failed_readback_does_not_report_success(self):
        def run(args,**kwargs):
            return types.SimpleNamespace(returncode=0,stdout='Mono: Playback 151 [100%] [on]')
        with self.assertRaises(RuntimeError):
            AlsaMixer(run).apply({'volume':60})

    def test_background_application_and_persistence(self):
        service=self.service(FakeMixer())
        revision=service.request({'volume':82,'muted':True})
        wait_for(lambda:service.read()['applied_version']==revision)
        self.assertEqual(service.read()['volume'],82)
        self.assertTrue(SettingsStore(self.path).read()['muted'])

    def test_drag_coalesces_pending_values_instead_of_building_a_queue(self):
        entered,release=threading.Event(),threading.Event()
        backend=FakeMixer()
        original=backend.apply
        def blocked(values):
            entered.set()
            release.wait(2)
            return original(values)
        backend.apply=blocked
        service=self.service(backend)
        service.request({'volume':10})
        self.assertTrue(entered.wait(1))
        for value in range(11,91):
            service.request({'volume':value})
        revision=service.request({'muted':True})
        release.set()
        wait_for(lambda:service.read()['applied_version']==revision)
        self.assertEqual(backend.requests,[{'volume':10},{'volume':90,'muted':True}])

    def test_device_failure_never_saves_an_unapplied_volume(self):
        backend=FakeMixer();backend.fail=True
        service=self.service(backend)
        service.request({'volume':40})
        wait_for(lambda:bool(service.read()['error']))
        self.assertFalse(service.read()['available'])
        self.assertFalse(self.path.exists())

    def test_saved_volume_is_restored_on_restart(self):
        self.store.update({'volume':64,'muted':True})
        self.store=SettingsStore(self.path)
        backend=FakeMixer();service=self.service(backend)
        wait_for(lambda:service.read()['available'] and not service.read()['pending'])
        self.assertEqual(backend.actual,{'volume':64,'muted':True})

    def test_external_volume_change_is_reflected(self):
        backend=FakeMixer();service=self.service(backend)
        wait_for(lambda:service.read()['available'])
        backend.actual['volume']=93
        wait_for(lambda:service.read()['volume']==93)


if __name__ == '__main__':
    unittest.main()
