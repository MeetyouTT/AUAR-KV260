"""Finalize only generated local migration records; no device/model work."""
from pathlib import Path
import hashlib
import json
import zipfile

HERE=Path(__file__).resolve().parent
PACKAGE=HERE.parent
copy_result=json.loads((HERE/'DEPENDENCY_MIGRATION_RESULT.json').read_text(encoding='utf-8'))
assert copy_result['status']=='COPIED_AND_HASH_VERIFIED'
locks=json.loads((HERE/'EFFECTIVE_ENVIRONMENT_LOCK_RESULT.json').read_text(encoding='utf-8'))
assert locks['status']=='EFFECTIVE_LOCKS_EXPORTED'
wheel=HERE/'wheels/omnivoice-0.2.1-py3-none-any.whl'
digest=hashlib.sha256(wheel.read_bytes()).hexdigest()
assert digest=='64aaca0b706eff3c8db844b855fd98aaaf59b7d8cde929d293ee0e01a968bcdf'
manifest=json.loads((HERE/'EXTERNAL_COPY_MANIFEST.json').read_text(encoding='utf-8'))
with zipfile.ZipFile(wheel) as archive:
    names=set(archive.namelist())
    for row in manifest:
        path=Path(row['target'])
        source_root=PACKAGE/'external_dependencies/source'
        if path.is_relative_to(source_root):
            relative=path.relative_to(source_root).as_posix()
            assert relative in names,relative
            assert hashlib.sha256(archive.read(relative)).hexdigest()==row['sha256'],relative
    assert archive.testzip() is None
files=[]
for path in HERE.rglob('*'):
    if path.is_file() and path.name!='DEPENDENCY_FINAL_HANDOFF.json':
        files.append(dict(path=path.relative_to(PACKAGE).as_posix(),bytes=path.stat().st_size,
                          sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
result=dict(schema='aura-external-dependencies-final-handoff-1',status='COMPLETE_LOCAL_COPY_AND_RECORDS',
    copied_resource_files=copy_result['files'],copied_resource_bytes=copy_result['bytes'],
    copied_resource_source_and_target_sha256_verified=True,
    environment_lock_summary=locks['environments'],
    own_source_wheel=dict(path=wheel.relative_to(PACKAGE).as_posix(),sha256=digest,
                         every_preserved_source_file_matches_wheel=True,zip_integrity_passed=True),
    script_verification='Two Python AST parses and two PowerShell parser checks passed; no new-host runtime executed.',
    production_tts_model='Already regular directory at E:/Win共享文件/语音共享文件/aura/models/tts/OmniVoice',
    general_llm_payload_in_package=False,private_keys_or_private_db_in_copies=False,venv_copied=False,
    tts_candidate_gguf_explicitly_classified=True,
    old_source_deleted_or_moved=False,device_or_model_invocation=False,
    required_new_host_work=['Install/rebuild runtime; read hardware and validate actual 5090 CUDA capability.',
        'Restore general LLM weights in external model storage or download exact artifact and verify known SHA.',
        'Update voice_python/network paths and remeasure GPU UUID/memory calibration; do not reuse old pth.',
        'Reconnect authorized board SSH under root handoff; preserve board-owned business/memory.'],
    files=files)
(HERE/'DEPENDENCY_FINAL_HANDOFF.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({k:v for k,v in result.items() if k!='files'},ensure_ascii=False))
