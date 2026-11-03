"""Preserve v20 r1 and fix exact-pinned empty sources plus child error codes."""
import ast
import hashlib
import json
from pathlib import Path


HERE = Path(__file__).resolve().parent
OLD = HERE.parent/'asr_threads_v20'
OLD_PACKAGE = '2fd9c809f3be89d96ee8efbea21147ea7159b4b853f4a12eb8c954684f0362fd'


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def replace_once(text, old, new):
    assert text.count(old) == 1
    return text.replace(old,new)


def write_json(name, value):
    (HERE/name).write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8')


old_manifest_raw = (OLD/'PACKAGE_MANIFEST.json').read_bytes()
assert sha(old_manifest_raw) == OLD_PACKAGE
old_manifest = json.loads(old_manifest_raw)
original = {}
for name,row in old_manifest['files'].items():
    raw = (OLD/name).read_bytes()
    assert sha(raw) == row['sha256']
    original[name] = raw
source = original['probe_small_threads.py'].decode('utf-8')
codes = {node.args[1].value for node in ast.walk(ast.parse(source))
    if isinstance(node,ast.Call) and isinstance(node.func,ast.Name) and node.func.id == 'require'
    and len(node.args) > 1 and isinstance(node.args[1],ast.Constant) and isinstance(node.args[1].value,str)}
codes.update({'ValueError','TypeError','RuntimeError','OSError','TimeoutError','MemoryError',
              'ImportError','ModuleNotFoundError','FileNotFoundError','Refused','PermissionError'})
assert all(len(code) <= 64 for code in codes)
code_text = ('CHILD_ERROR_CODES = frozenset({\n'
             + ''.join('    ' + repr(code) + ',\n' for code in sorted(codes)) + '})\n')
updated = replace_once(source,"require(0<path.stat().st_size<=maximum,'SIZE_REJECTED')",
    "require(0<=path.stat().st_size<=maximum,'SIZE_REJECTED')")
updated = replace_once(updated,'ORDER=(3,2,2,3)\n','ORDER=(3,2,2,3)\n'+code_text)
helpers = '''def allowed_child_code(value):
    return value if type(value) is str and len(value)<=64 and value in CHILD_ERROR_CODES else None


def child_error_code(stdout):
    if type(stdout) is not str or len(stdout)>=65536:
        return None
    try:
        value=json.loads(stdout)
    except (ValueError,RecursionError):
        return None
    if not isinstance(value,dict) or value.get('status')!='REFUSED':
        return None
    return allowed_child_code(value.get('error_code'))


'''
updated = replace_once(updated,'def run_child(threads,package_sha,deadline):\n',
    helpers+'def run_child(threads,package_sha,deadline):\n')
updated = replace_once(updated,
    "        require(process.returncode==0 and len(stdout)<65536,'OWNED_ASR_SLOT_FAILED')\n",
    "        require(len(stdout)<65536,'OWNED_ASR_SLOT_FAILED')\n"
    "        if process.returncode!=0:\n"
    "            error=Refused('OWNED_ASR_SLOT_FAILED')\n"
    "            error.child_error_code=child_error_code(stdout)\n"
    "            raise error\n")
updated = replace_once(updated,
    "            error_code=str(error) if isinstance(error,Refused) else type(error).__name__,production_changed=False)\n",
    "            error_code=str(error) if isinstance(error,Refused) else type(error).__name__,\n"
    "            child_error_code=allowed_child_code(getattr(error,'child_error_code',None)),production_changed=False)\n")
ast.parse(updated)
changed = dict(original)
changed['probe_small_threads.py'] = updated.encode('utf-8')
for name,raw in changed.items():
    (HERE/name).write_bytes(raw)
for name in ('test_probe.py','test_v20_bindings.py'):
    (HERE/name).write_bytes((OLD/name).read_bytes())
manifest = dict(old_manifest)
manifest['previous_v20_package_sha256'] = OLD_PACKAGE
manifest['revision'] = 'r2_exact_empty_source_and_child_codes'
manifest['files'] = {name:dict(sha256=sha(raw),bytes=len(raw)) for name,raw in changed.items()}
write_json('PACKAGE_MANIFEST.json',manifest)
package_sha = sha((HERE/'PACKAGE_MANIFEST.json').read_bytes())
stage = '/home/root/aura-public-small-threads-v20-r2-20261031/' + package_sha[:16]
handoff = json.loads((OLD/'HANDOFF.json').read_bytes())
handoff.update(status='LOCAL_PREPARED_PENDING_R2_TESTS',package_sha256=package_sha,stage=stage,
    command='python3 -B '+stage+'/probe_small_threads.py --package-sha256 '+package_sha+' --execute-root-only',
    dry_command='python3 -B '+stage+'/probe_small_threads.py --package-sha256 '+package_sha,
    files=manifest['files'],previous_failed_package_sha256=OLD_PACKAGE,
    previous_failure_receipt=str(OLD/'ACTUAL_ABBA_1793502852731598600.json'),
    exact_empty_sources_allowed=True,sha256_still_required_for_all_sizes=True,
    child_error_output='bounded fixed-enum error_code from structured stdout only')
handoff.pop('local_tests',None)
handoff.pop('test_source_sha256',None)
write_json('HANDOFF.json',handoff)
write_json('R2_CHANGE_PROOF.json',dict(original_package_sha256=OLD_PACKAGE,
    previous_failure_receipt_sha256=sha((OLD/'ACTUAL_ABBA_1793502852731598600.json').read_bytes()),
    original_sources_preserved=True,baseline_byte_exact=True,comparator_byte_exact=True,helper_byte_exact=True,
    original_source_checks_retained=['absolute-path','non-symlink','maximum-size','exact-SHA256'],
    edits=['allow-zero-byte-source-with-exact-hash','safe-child-error-enum-propagation'],
    child_error_codes=sorted(codes),child_code_max_length=64,child_stdout_max_characters=65535,
    stderr_exported=False,actual_test_executed=False))
print(json.dumps(dict(status='R2_PREPARED',package_sha256=package_sha,stage=stage)))
