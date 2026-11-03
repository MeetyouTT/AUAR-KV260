"""One focused check of root's actual dangling-stage preflight fix."""
import ast
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
from unittest import mock

HERE=Path(__file__).resolve().parent
SOURCE=HERE.parent/'camera/six_file_transaction_template.py'
raw=SOURCE.read_bytes()
assert hashlib.sha256(raw).hexdigest()=='32329668ea3dfb63744e58a7866025cb7ba1f0986f72d30948b8c93ceb401a6a'
tree=ast.parse(raw)
klass=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='SixFileTransaction')
recover=next(n for n in klass.body if isinstance(n,ast.FunctionDef) and n.name=='recover_plan')
assert any(isinstance(n,ast.BoolOp) and isinstance(n.op,ast.Or)
    and {call.func.attr for call in n.values if isinstance(call,ast.Call) and isinstance(call.func,ast.Attribute)}=={'exists','is_symlink'}
    for n in ast.walk(recover))
spec=importlib.util.spec_from_file_location('actual_fixed_tx_stage_review',SOURCE)
tx=importlib.util.module_from_spec(spec);spec.loader.exec_module(tx)
temp=tempfile.TemporaryDirectory(prefix='tx-fixed-generated-',dir=HERE)
root=Path(temp.name).resolve()
assert root.is_relative_to(HERE.resolve()) and root.name.startswith('tx-fixed-generated-')
try:
    targets=root/'targets';payload=root/'payload';targets.mkdir();payload.mkdir();records=[]
    for name in tx.NAMES:
        before=('before-'+name).encode();after=('after-'+name).encode()
        target=targets/name;target.write_bytes(before);content=payload/name;content.write_bytes(after)
        records.append({'name':name,'target':str(target),'payload':str(content),
            'before_sha256':tx.digest(before),'after_sha256':tx.digest(after)})
    backup=root/'backup'
    def instance():return tx.SixFileTransaction(records,backup,lambda:None,lambda:None,directory_sync=lambda path:None)
    prepared=instance();prepared.prepare();stage=Path(prepared.plan['files'][3]['stage'])
    marker=b'isolated-only-occupied-dangling-name-model';stage.write_bytes(marker)
    original_exists=Path.exists;original_symlink=Path.is_symlink
    def exists(path):return False if path==stage else original_exists(path)
    def is_symlink(path):return True if path==stage else original_symlink(path)
    observed={}
    with mock.patch.object(Path,'exists',exists),mock.patch.object(Path,'is_symlink',is_symlink):
        for label,operation in (('recover_plan',lambda:instance().recover_plan()),
                                ('commit_recover',lambda:instance().commit(recover=True))):
            try:operation()
            except RuntimeError:observed[label+'_rejected_before_commit']=True
            else:raise RuntimeError('Fixed dangling stage was accepted')
    assert [tx.digest(Path(row['target']).read_bytes()) for row in records]==[row['before_sha256'] for row in records]
    assert stage.read_bytes()==marker and SOURCE.read_bytes()==raw
    result={'status':'PASS_ACTUAL_ROOT_FIX_TARGETED_DANGLING_MODEL',
        'template_sha256':hashlib.sha256(raw).hexdigest(),'ast_has_exists_or_is_symlink_guard':True,
        'results':observed,'all_six_targets_unchanged':True,'unknown_stage_name_and_bytes_preserved':True,
        'filesystem_model':'mocked dangling-link pathlib observations plus real occupied generated stage file',
        'actual_linux_executor_tested':False,'actual_windows_symlink_created':False,
        'directory_fsync_mocked_for_windows_fixture':True,
        'board_or_network_or_live_guard_called':False,'original_template_modified':False,
        'full_unchanged_suite_rerun':False}
finally:
    assert root.is_relative_to(HERE.resolve()) and root.name.startswith('tx-fixed-generated-')
    temp.cleanup()
(HERE/'TRANSACTION_DANGLING_STAGE_FIXED.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
print(json.dumps(result))
