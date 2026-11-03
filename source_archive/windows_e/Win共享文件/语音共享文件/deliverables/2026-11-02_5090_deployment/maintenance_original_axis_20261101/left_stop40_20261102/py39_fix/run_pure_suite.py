import ast
import datetime
import hashlib
import io
import json
from pathlib import Path
import sys
import unittest

HERE=Path(__file__).resolve().parent
import test_left_episode
import test_hardware_slew

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
review=json.loads((HERE/'INDEPENDENT_REVIEW.json').read_text(encoding='utf-8'))
records=[]
for record in review['records']:
    name=record['file'];before=HERE/'before'/name;after=HERE/'candidate'/name
    assert sha(before)==record['before'] and sha(after)==record['after']
    if after.suffix=='.py':ast.parse(after.read_bytes())
    records.append(dict(file=name,sha256=sha(after),changed=sha(before)!=sha(after)))
assert len(records)==25 and sum(r['changed'] for r in records)==3
stream=io.StringIO()
suite=unittest.TestSuite([unittest.defaultTestLoader.loadTestsFromModule(test_left_episode),
                         unittest.defaultTestLoader.loadTestsFromModule(test_hardware_slew)])
result=unittest.TextTestRunner(stream=stream,verbosity=2).run(suite)
assert not any(x in sys.modules for x in ('vsrv_driver','vsrv_transport','live_writer'))
log=stream.getvalue();(HERE/'PURE_TESTS.log').write_text(log,encoding='utf-8')
receipt=dict(status='PASS' if result.wasSuccessful() else 'FAIL',utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
    tests_run=result.testsRun,failures=len(result.failures),errors=len(result.errors),skipped=len(result.skipped),
    targeted_tests=15,original_hardware_slew_tests=16,records=records,
    original_hardware_test_sha256=sha(Path(test_hardware_slew.__file__)),fixture_sha256=sha(Path(test_left_episode.ARCHIVE/'tests/fixtures/test_recenter.py')),
    test_source_sha256=sha(HERE/'test_left_episode.py'),native_trajectory_called=False,devices_opened=False,board_connected=False)
(HERE/'PURE_TESTS.json').write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8')
print(log);print(json.dumps({k:v for k,v in receipt.items() if k!='records'},indent=2))
sys.exit(0 if result.wasSuccessful() else 1)
