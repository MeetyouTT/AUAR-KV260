"""Empty-source and structured-child-failure regressions, all local synthetic."""
from contextlib import ExitStack
import io
import json
from pathlib import Path
import sys
import tempfile
import time
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import probe_small_threads as probe
from test_probe import ProbeTests
from test_v20_bindings import V20Bindings


HERE = Path(__file__).resolve().parent


class R2Tests(unittest.TestCase):
    def test_exact_hash_empty_source_is_accepted(self):
        with tempfile.TemporaryDirectory(prefix='aura-public-empty-source-') as name:
            path = Path(name).resolve()/'__init__.py'
            path.write_bytes(b'')
            self.assertEqual(probe.read_pinned(path,probe.sha(b'')),b'')

    def test_empty_source_with_wrong_or_configuration_hash_is_rejected(self):
        with tempfile.TemporaryDirectory(prefix='aura-public-empty-source-') as name:
            path = Path(name).resolve()/'public-config.json'
            path.write_bytes(b'')
            for digest in ('0'*64,probe.CONFIG_SHA):
                with self.subTest(digest=digest):
                    with self.assertRaisesRegex(probe.Refused,'SOURCE_PIN_CHANGED'):
                        probe.read_pinned(path,digest)

    def test_child_code_allows_fixed_enum_without_extra_private_fields(self):
        raw = json.dumps(dict(status='REFUSED',error_code='SOURCE_PIN_CHANGED',message='PRIVATE_MESSAGE'))
        code = probe.child_error_code(raw)
        self.assertEqual(code,'SOURCE_PIN_CHANGED')
        self.assertNotIn('PRIVATE_MESSAGE',json.dumps(dict(child_error_code=code)))

    def test_malformed_unknown_oversized_or_wrong_status_child_output_has_no_code(self):
        inputs = [
            'PRIVATE_NATIVE_OUTPUT',
            json.dumps(dict(status='REFUSED',error_code='PRIVATE_MESSAGE')),
            json.dumps(dict(status='REFUSED',error_code=['PRIVATE_MESSAGE'])),
            json.dumps(dict(status='REFUSED',error_code='x'*65)),
            json.dumps(dict(status='PUBLIC_ASR_SLOT_MEASURED',error_code='SOURCE_PIN_CHANGED')),
            json.dumps(['PRIVATE_MESSAGE']),
            ' ' * 65536 + json.dumps(dict(status='REFUSED',error_code='SOURCE_PIN_CHANGED')),
        ]
        for raw in inputs:
            with self.subTest(length=len(raw)):
                self.assertIsNone(probe.child_error_code(raw))

    def test_run_child_retains_only_safe_structured_failure_and_drops_stderr(self):
        stdout = json.dumps(dict(status='REFUSED',error_code='SHERPA_VERSION_CHANGED',detail='PRIVATE_DETAIL'))
        process = SimpleNamespace(pid=345678,returncode=2,
            communicate=lambda **kwargs:(stdout,'PRIVATE_STDERR'),poll=lambda:2)
        with patch.object(probe.subprocess,'Popen',return_value=process), \
                patch.object(probe,'process_identity',return_value=dict(pid=345678,birth_ticks=1,command_sha256='a'*64)), \
                patch.object(probe.os,'killpg',side_effect=ProcessLookupError,create=True):
            with self.assertRaises(probe.Refused) as raised:
                probe.run_child(3,'a'*64,time.monotonic()+20)
        error = raised.exception
        self.assertEqual(str(error),'OWNED_ASR_SLOT_FAILED')
        self.assertEqual(error.child_error_code,'SHERPA_VERSION_CHANGED')
        self.assertNotIn('PRIVATE',json.dumps(dict(error=str(error),child=error.child_error_code)))

    def test_parent_propagates_safe_child_code_and_stays_metadata_only(self):
        error = probe.Refused('OWNED_ASR_SLOT_FAILED')
        error.child_error_code = 'SHERPA_VERSION_CHANGED'
        digest = probe.sha((HERE/'PACKAGE_MANIFEST.json').read_bytes())
        with ExitStack() as stack:
            stack.enter_context(patch.object(sys,'argv',['probe','--package-sha256',digest,'--execute-root-only']))
            stack.enter_context(patch.object(probe.platform,'system',return_value='Linux'))
            stack.enter_context(patch.object(probe.platform,'machine',return_value='aarch64'))
            stack.enter_context(patch.object(probe.os,'PRIO_PROCESS',0,create=True))
            stack.enter_context(patch.object(probe.os,'getpriority',return_value=0,create=True))
            stack.enter_context(patch.object(probe.os,'sched_getaffinity',return_value={0,1,2,3},create=True))
            stack.enter_context(patch.object(probe,'guard',return_value={}))
            stack.enter_context(patch.object(probe,'run_child',side_effect=error))
            value = probe.main()
        self.assertEqual(value['status'],'PUBLIC_ABBA_STOPPED')
        self.assertEqual(value['error_code'],'OWNED_ASR_SLOT_FAILED')
        self.assertEqual(value['child_error_code'],'SHERPA_VERSION_CHANGED')
        self.assertEqual(value['results'],[])


if __name__ == '__main__':
    suite = unittest.TestSuite()
    for cls in (ProbeTests,V20Bindings,R2Tests):
        suite.addTests(unittest.defaultTestLoader.loadTestsFromTestCase(cls))
    stream = io.StringIO()
    result = unittest.TextTestRunner(stream=stream,verbosity=2).run(suite)
    report = dict(status='PASS' if result.wasSuccessful() else 'FAIL',tests=result.testsRun,
        failures=len(result.failures),errors=len(result.errors),log=stream.getvalue(),
        device_or_model_private_database_or_network_access=False,
        package_sha256=probe.sha((HERE/'PACKAGE_MANIFEST.json').read_bytes()))
    path = HERE/'LOCAL_TESTS_R2.json'
    path.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    if result.wasSuccessful():
        handoff_path = HERE/'HANDOFF.json'
        handoff = json.loads(handoff_path.read_bytes())
        handoff['status'] = 'LOCAL_READY_NO_DEVICE_OR_MODEL_EXECUTION'
        handoff['local_tests'] = dict(path=str(path),sha256=probe.sha(path.read_bytes()),passed=result.testsRun)
        handoff['test_source_sha256'] = probe.sha(Path(__file__).read_bytes())
        handoff_path.write_text(json.dumps(handoff,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report))
    raise SystemExit(0 if result.wasSuccessful() else 1)
