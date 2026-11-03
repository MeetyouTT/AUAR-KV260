"""Seal only this helper's local mock evidence; never runs its actual CLI."""
import datetime
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import sys
import threading
import time
import unittest
import xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parent


def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    spec=importlib.util.spec_from_file_location('x11_mock_tests',ROOT/'test_x11_normal_close.py')
    module=importlib.util.module_from_spec(spec);sys.modules[spec.name]=module;spec.loader.exec_module(module)
    before=tuple(threading.enumerate());stream=io.StringIO();started=time.perf_counter()
    result=unittest.TextTestRunner(stream=stream,verbosity=2).run(unittest.defaultTestLoader.loadTestsFromModule(module))
    elapsed=time.perf_counter()-started;leaked=[t.name for t in threading.enumerate() if t not in before]
    (ROOT/'helper_mock_tests.log').write_text(stream.getvalue(),encoding='utf-8')
    report=dict(tests=result.testsRun,failures=len(result.failures),errors=len(result.errors),skipped=len(result.skipped),
        seconds=elapsed,new_live_threads=leaked,success=result.wasSuccessful() and not leaked,
        real_x11_calls=0,board_calls=0,service_calls=0,model_calls=0,actual_close_requests=0)
    (ROOT/'helper_mock_tests.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    xml=ET.Element('testsuite',name='x11_normal_close_mock',tests=str(result.testsRun),
        failures=str(len(result.failures)),errors=str(len(result.errors)),time=str(elapsed))
    ET.ElementTree(xml).write(ROOT/'helper_mock_tests.xml',encoding='utf-8',xml_declaration=True)
    if not report['success']:raise RuntimeError('Mock contracts failed')
    names=('x11_normal_close.py','test_x11_normal_close.py','prepare_original_close_plan.py','finalize_helper.py',
           'original_gui.plan.json','launcher_review.json','HELPER_REVIEW.txt','helper_mock_tests.json','helper_mock_tests.log','helper_mock_tests.xml')
    manifest=dict(schema_version=1,status='SOURCE_REVIEWED_ROOT_EXECUTION_ONLY',
        utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        default_mode='inspect_only',root_only_actual_execution=True,
        baseline_input_sha256=digest(ROOT/'actual_ui_baseline.json'),
        files={name:dict(sha256=digest(ROOT/name),bytes=(ROOT/name).stat().st_size) for name in names},
        validation=report)
    (ROOT/'helper_manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    print(json.dumps(dict(status=manifest['status'],tests=result.testsRun,seconds=elapsed,
        helper_sha256=digest(ROOT/'x11_normal_close.py'),plan_sha256=digest(ROOT/'original_gui.plan.json'),
        manifest_sha256=digest(ROOT/'helper_manifest.json'),new_live_threads=leaked)))


if __name__=='__main__':main()
