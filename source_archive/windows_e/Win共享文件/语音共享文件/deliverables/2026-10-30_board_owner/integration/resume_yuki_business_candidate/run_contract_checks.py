"""Run only the source candidate's short injected contracts and save evidence."""
import datetime
import importlib.util
import io
import json
from pathlib import Path
import threading
import time
import unittest
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parent


class Result(unittest.TextTestResult):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.cases = []
    def startTest(self, test):
        self.started = time.perf_counter()
        super().startTest(test)
    def stopTest(self, test):
        self.cases.append(dict(name=test.id(), seconds=time.perf_counter()-self.started))
        super().stopTest(test)


def main():
    spec = importlib.util.spec_from_file_location('yuki_candidate_contracts', ROOT/'test_candidate_contracts.py')
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    before = tuple(threading.enumerate())
    stream = io.StringIO()
    started = time.perf_counter()
    result = unittest.TextTestRunner(stream=stream, verbosity=2, resultclass=Result).run(
        unittest.defaultTestLoader.loadTestsFromModule(module))
    elapsed = time.perf_counter()-started
    leaked = [thread.name for thread in threading.enumerate() if thread not in before]
    report = dict(schema_version=1, utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        tests=result.testsRun, failures=len(result.failures), errors=len(result.errors), skipped=len(result.skipped),
        elapsed_seconds=elapsed, new_live_threads=leaked, success=result.wasSuccessful() and not leaked,
        services_called=False, devices_opened=False, private_databases_read=False,
        models_executed=False, actual_performance_test=False,
        fixtures='Public text, in-RAM PCM, fake ASR/controller/player/native widget; no socket/GPU/GLES/board',
        command='D:\\AIModels\\speaker-identity\\venv\\Scripts\\python.exe -B '+str(ROOT/'run_contract_checks.py'),
        cases=result.cases)
    (ROOT/'contract_tests.log').write_text(stream.getvalue(), encoding='utf-8')
    (ROOT/'contract_tests.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    xml = ET.Element('testsuite', name='yuki_business_candidate', tests=str(result.testsRun),
                     failures=str(len(result.failures)), errors=str(len(result.errors)), time=str(elapsed))
    failures = {test.id(): detail for test, detail in result.failures}
    errors = {test.id(): detail for test, detail in result.errors}
    for row in result.cases:
        case = ET.SubElement(xml, 'testcase', name=row['name'], time=str(row['seconds']))
        if row['name'] in failures: ET.SubElement(case, 'failure').text = failures[row['name']]
        if row['name'] in errors: ET.SubElement(case, 'error').text = errors[row['name']]
    ET.ElementTree(xml).write(ROOT/'contract_tests.xml', encoding='utf-8', xml_declaration=True)
    print(json.dumps({key: report[key] for key in ('tests','failures','errors','skipped','elapsed_seconds','new_live_threads','success')}))
    return 0 if report['success'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
