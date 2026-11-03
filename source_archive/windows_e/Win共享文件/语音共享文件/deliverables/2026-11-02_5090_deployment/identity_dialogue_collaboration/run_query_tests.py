"""Select exact baseline or the one-file candidate; no alternate project checkout imports."""
import hashlib,importlib,io,json,sys,unittest
from pathlib import Path
HERE=Path(__file__).resolve().parent
baseline='--baseline' in sys.argv
if baseline:sys.argv.remove('--baseline')
v2='--v2' in sys.argv
if v2:sys.argv.remove('--v2')
manifest=json.loads((HERE/'SOURCE_MANIFEST.json').read_text(encoding='utf-8'))
for relative,row in manifest['baseline_files'].items():
    assert hashlib.sha256((HERE/'baseline'/relative).read_bytes()).hexdigest()==row['sha256'],relative
sys.path.insert(0,str(HERE/'baseline'))
import common,tools
common.__path__=[str(HERE/'baseline/common')]
tools.__path__=[str(HERE/'baseline/tools')]
if not baseline:
    tools.__path__.insert(0,str(HERE/'candidate/tools'))
    for relative,row in manifest['files'].items():
        assert hashlib.sha256((HERE/'candidate'/relative).read_bytes()).hexdigest()==row['sha256']
suite=unittest.defaultTestLoader.discover(str(HERE),pattern='test_identity_query_isolation.py')
report=HERE/(('BASELINE_QUERY_TESTS' if baseline else 'CANDIDATE_QUERY_TESTS')+('_V2' if v2 else '')+'.log')
assert not report.exists()
buffer=io.StringIO()
result=unittest.TextTestRunner(verbosity=2,stream=buffer).run(suite)
report.write_text(buffer.getvalue(),encoding='utf-8')
print(json.dumps({'baseline':baseline,'tests':result.testsRun,'failures':len(result.failures),
    'errors':len(result.errors),'passed':result.wasSuccessful(),'report':str(report)}))
raise SystemExit(not result.wasSuccessful())
