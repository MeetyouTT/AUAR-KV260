"""Create a test-harness patch and offline comparisons; no board operations."""
import ast
import contextlib
import datetime
import difflib
import hashlib
import io
import json
from pathlib import Path
import re

ROOT=Path('/home/ghmd/kv260-runtime-live-20261003-retry1/agent_review')
OLD=Path('/home/ghmd/kv260-runtime-live-20261003/reviewed_payload/actions/10_start.py')
NEW=ROOT/'10_start.py'
patch=''.join(difflib.unified_diff(OLD.read_text().splitlines(True),NEW.read_text().splitlines(True),
    fromfile='original_reviewed/actions/10_start.py',tofile='retry1_reviewed/actions/10_start.py'))
patch_path=ROOT/'10_start_kernel_ring.patch'
if patch_path.exists():
    assert patch_path.read_text()==patch
else:
    patch_path.write_text(patch)
ns={}
exec(compile((ROOT/'kernel_interval.py').read_bytes(),'kernel_interval','exec'),ns)
compare=ns['compare_kernel_logs']
base=['[ {:8.6f}] baseline line {}'.format(i,i) for i in range(30)]
known='[ 31.000000] OF: ERROR: memory leak, expected refcount 1 instead of 2 /axi/zyxclmm_drm'
warning='[ 31.000000] OF: overlay: WARNING: memory leak will occur'
unknown='[ 31.000000] ERROR unrelated failure'
def raw(lines):return ('\n'.join(lines)+'\n').encode()
cases=[
 ('unchanged',base,base,False,True),
 ('append-without-roll',base,base+[warning],False,True),
 ('roll-stock-known-once',base,base[4:]+[known],True,True),
 ('roll-candidate-property-warning',base,base[4:]+[warning],False,True),
 ('candidate-known-ref-error-forbidden',base,base[4:]+[known],False,False),
 ('stock-known-twice-forbidden',base,base[4:]+[known,known+' duplicate'],True,False),
 ('stock-unrelated-error-forbidden',base,base[4:]+[known,unknown],True,False),
 ('missing-anchor-gap',base,['[ 100.000000] entirely replaced ring'],False,False),
 ('ambiguous-anchor-gap',base,base+base,False,False),
 ('empty-before-gap',[],base,False,False)]
OUT=ROOT/('offline-kernel-fixtures-'+datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'))
OUT.mkdir(exist_ok=False)
checks=[]

# Extract and run only the comparison function from the actual action source.
# No board action statement is compiled or executed by this fixture.
tree=ast.parse(NEW.read_text())
function=next(node for node in tree.body if isinstance(node,ast.FunctionDef) and node.name=='review_kernel_interval')
func_tree=ast.Module(body=[function],type_ignores=[])
namespace={'Path':Path,'WORK':OUT,'json':json,'re':re,'hashlib':hashlib,
           'digest':lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()}
exec(compile(func_tree,'offline_action_comparison','exec'),namespace)
for label,old,new,allow,expected in cases:
    before=OUT/(label+'.before.log');before.write_bytes(raw(old))
    after=OUT/(label+'.after.log');after.write_bytes(raw(new))
    pure=compare(before.read_bytes(),after.read_bytes(),allow)
    assert pure['passed']==expected,label
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            actual=namespace['review_kernel_interval'](before,after,label,allow_stock_remove=allow)
        passed=True
    except AssertionError:
        passed=False
        actual=json.loads((OUT/(label+'.json')).read_text())
    assert passed==expected,label+' action mismatch'
    assert actual['new_lines']==pure['new_lines']
    assert actual['continuity_confirmed']==pure['continuity_confirmed']
    checks.append({'case':label,'expected_pass':expected,'action_pass':passed,'fixture_verified':True,
                   'continuity_confirmed':actual['continuity_confirmed'],
                   'error_lines':actual['new_error_lines']})

diagnostic=Path('/home/ghmd/kv260-runtime-live-20261003/evidence/failure-diagnosis.ring.output')
diagnostic_text=diagnostic.read_text()
diag={'kernel_sizes':[{'filename':m[1],'lines':int(m[2]),'bytes':int(m[3])}
                     for m in re.finditer(r'^KERNEL (\S+) (\d+) (\d+) FIRST',diagnostic_text,re.M)],
      'anchor_end_indexes':json.loads(re.search(r'^ANCHOR_END_INDEXES (.*)$',diagnostic_text,re.M)[1]),
      'new_lines':json.JSONDecoder().raw_decode(diagnostic_text.split('NEW_LINES ',1)[1])[0]}
checks.append({'case':'real_first_attempt_diagnosis','evidence':str(diagnostic),
    'sha256':hashlib.sha256(diagnostic.read_bytes()).hexdigest(),'diagnosis':diag,
    'limitation':'Diagnostic summary is separate from the full raw-log comparison below'})
real_before=Path('/home/ghmd/kv260-runtime-live-20261003/board_evidence/logs/20211120T011221385182Z-before-original-remove-kernel.log')
real_after=Path('/home/ghmd/kv260-runtime-live-20261003/board_evidence/logs/20211120T011221723183Z-after-original-remove-kernel.log')
pure=compare(real_before.read_bytes(),real_after.read_bytes(),True)
with contextlib.redirect_stdout(io.StringIO()):
    actual=namespace['review_kernel_interval'](real_before,real_after,'real-stock-remove',allow_stock_remove=True)
assert actual['passed'] and actual['anchor_after_positions']==[625]
assert actual['new_lines']==diag['new_lines'] and len(actual['new_lines'])==4
assert len(actual['permitted_stock_remove_errors'])==1 and not actual['unexpected_errors']
assert actual['new_lines']==pure['new_lines'] and actual['old_prefix_removed_rows_estimate']==4
checks.append({'case':'real_raw_logs_original_remove','fixture_verified':True,'comparison':actual})
compile(NEW.read_bytes(),str(NEW),'exec')
result={'passed':True,'board_commands_executed':False,'source_old_sha256':hashlib.sha256(OLD.read_bytes()).hexdigest(),
        'source_new_sha256':hashlib.sha256(NEW.read_bytes()).hexdigest(),'checks':checks}
(ROOT/'KERNEL_PATCH_REVIEW.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({'passed':True,'cases':len(cases),'new_sha256':result['source_new_sha256'],
                 'real_logs_verified':True,'evidence':str(OUT),
                 'patch':str(ROOT/'10_start_kernel_ring.patch')},indent=2))
