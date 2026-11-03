"""One isolated recovery edge. Never invokes Linux CLI/live_guard or board."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import tempfile
from unittest import mock

HERE=Path(__file__).resolve().parent
SOURCE=HERE.parent/'camera/six_file_transaction_template.py'
raw=SOURCE.read_bytes()
spec=importlib.util.spec_from_file_location('isolated_tx_review',SOURCE)
tx=importlib.util.module_from_spec(spec);spec.loader.exec_module(tx)
temp=tempfile.TemporaryDirectory(prefix='tx-review-generated-',dir=HERE)
root=Path(temp.name).resolve()
assert root.is_relative_to(HERE.resolve()) and root.name.startswith('tx-review-generated-')
result={'source_sha256':hashlib.sha256(raw).hexdigest(),'board_or_network_called':False,
    'original_template_modified':False,'test_scope':'one isolated filesystem-core dangling-stage recovery case'}
try:
    targets=root/'targets';payload=root/'payload';targets.mkdir();payload.mkdir();records=[]
    for name in tx.NAMES:
        before=('before-'+name).encode();after=('after-'+name).encode()
        target=targets/name;target.write_bytes(before)
        content=payload/name;content.write_bytes(after)
        records.append({'name':name,'target':str(target),'payload':str(content),
            'before_sha256':tx.digest(before),'after_sha256':tx.digest(after)})
    backup=root/'backup'
    def instance(module=tx):
        return module.SixFileTransaction(records,backup,lambda:None,lambda:None,directory_sync=lambda path:None)
    original=instance();original.prepare()
    stage=Path(original.plan['files'][3]['stage'])
    assert stage.resolve().is_relative_to(root) and tx.digest(stage.read_bytes())==records[3]['after_sha256']
    stage.unlink()  # Only the just-generated known stage, within this fixture.
    def exercise():
        assert not stage.exists() and stage.is_symlink() and os.path.lexists(stage)
        recovered=instance();recovered.recover_plan()
        recovered.current([{row['before_sha256'],row['after_sha256']} for row in records])
        result['recover_dryrun_core_accepted_dangling_stage']=True
        try:recovered.commit(recover=True)
        except Exception as error:result['apply_error_type']=type(error).__name__
        else:raise RuntimeError('Dangling stage unexpectedly committed')
        vector=[tx.digest(Path(row['target']).read_bytes()) for row in records]
        assert vector==[row['after_sha256'] if index<3 else row['before_sha256'] for index,row in enumerate(records)]
        result['known_targets_committed_before_refusal']=3
        result['unknown_stage_name_preserved']=stage.is_symlink() and not stage.exists()
        result['unknown_destination_created']=(root/'missing-stage-target.bin').exists()
        code=raw.decode().replace('\r\n','\n')
        needle="            if Path(row['stage']).exists():pinned({'path':row['stage'],'sha256':row['after_sha256']})"
        assert code.count(needle)==1
        fixed=code.replace(needle,"            if Path(row['stage']).exists() or Path(row['stage']).is_symlink():pinned({'path':row['stage'],'sha256':row['after_sha256']})")
        namespace={'__name__':'validation_only_tx_fix'};exec(compile(fixed,'<one-branch-prototype>','exec'),namespace)
        changed=namespace['SixFileTransaction'](records,backup,lambda:None,lambda:None,directory_sync=lambda path:None)
        try:changed.recover_plan()
        except RuntimeError:result['minimal_fix_rejects_during_recovery_precheck']=True
        else:raise RuntimeError('Minimal fix did not reject dangling stage')
        assert [tx.digest(Path(row['target']).read_bytes()) for row in records]==vector
        result['minimal_fix_writes_no_target']=True
        result['status']='RECOVERY_DRYRUN_FALSE_POSITIVE_REPRODUCED_MINIMAL_FIX_PASS'
    try:os.symlink(str(root/'missing-stage-target.bin'),str(stage))
    except OSError as error:
        # Standard Windows may not grant symlink creation. Model exactly the
        # dangling-name observations (exists=False, is_symlink=True, EEXIST on
        # O_EXCL) while all six real byte/CAS files remain isolated fixtures.
        result.update(symlink_creation_error_type=type(error).__name__,
            filesystem_model='mocked dangling-link pathlib observations with a real occupied stage name',
            actual_windows_symlink_created=False)
        marker=b'isolated-simulated-dangling-link-name';stage.write_bytes(marker)
        original_exists=Path.exists;original_symlink=Path.is_symlink
        def exists(path):return False if path==stage else original_exists(path)
        def is_symlink(path):return True if path==stage else original_symlink(path)
        with mock.patch.object(Path,'exists',exists),mock.patch.object(Path,'is_symlink',is_symlink):exercise()
        assert stage.read_bytes()==marker
        result['simulated_unknown_stage_bytes_preserved']=True
    else:
        result.update(filesystem_model='actual local dangling symlink',actual_windows_symlink_created=True)
        exercise()
    assert SOURCE.read_bytes()==raw
finally:
    assert root.is_relative_to(HERE.resolve()) and root.name.startswith('tx-review-generated-')
    temp.cleanup()
(HERE/'TRANSACTION_DANGLING_STAGE_REPRO.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
print(json.dumps(result))
