"""Original synthetic speaker/identity regressions with the one-file candidate."""
import contextlib,hashlib,io,json,os,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
PROJECT=HERE.parents[2]
v2='--v2' in sys.argv
if v2:sys.argv.remove('--v2')
label='_V2' if v2 else ''
manifest=json.loads((HERE/'SOURCE_MANIFEST.json').read_text(encoding='utf-8'))
for relative,row in manifest['baseline_files'].items():
    assert hashlib.sha256((HERE/'baseline'/relative).read_bytes()).hexdigest()==row['sha256'],relative
sys.path.insert(0,str(HERE/'baseline'))
import common,tools
common.__path__=[str(HERE/'baseline/common')]
tools.__path__=[str(HERE/'candidate/tools'),str(HERE/'baseline/tools')]
os.environ['PYTEST_DISABLE_PLUGIN_AUTOLOAD']='1'
import pytest
temporary=HERE/('original_regression_temp'+label)
assert not temporary.exists() and temporary.resolve().parent==HERE.resolve()
tests=PROJECT/'aura/tests/framework'
selected=[tests/'test_board_speaker_business.py',tests/'test_speaker_identity.py']
assert all(path.is_file() for path in selected)
source_manifest={str(p):{'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'bytes':p.stat().st_size} for p in selected}
(HERE/('REGRESSION_INPUTS'+label+'.json')).write_text(json.dumps(source_manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
capture=io.StringIO()
with contextlib.redirect_stdout(capture),contextlib.redirect_stderr(capture):
    rc=pytest.main(['-q','-p','no:cacheprovider','--import-mode=importlib','--rootdir',str(HERE),
        '--confcutdir',str(HERE),'--basetemp',str(temporary),'--junitxml='+str(HERE/('ORIGINAL_REGRESSION'+label+'.xml')),*map(str,selected)])
(HERE/('ORIGINAL_REGRESSION'+label+'.log')).write_text(capture.getvalue(),encoding='utf-8')
print(json.dumps({'exit_code':int(rc),'report':str(HERE/('ORIGINAL_REGRESSION'+label+'.log'))}))
raise SystemExit(rc)
