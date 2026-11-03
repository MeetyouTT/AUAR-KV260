import hashlib,json,shutil
from pathlib import Path
HERE=Path(__file__).resolve().parent
target=HERE/'v1';assert not target.exists();target.mkdir()
names=['candidate/tools/unified_identity_binding.py','SOURCE_MANIFEST.json','CANDIDATE.diff',
    'test_identity_query_isolation.py','run_query_tests.py','run_original_regressions.py',
    'BASELINE_QUERY_TESTS.log','CANDIDATE_QUERY_TESTS.log','ORIGINAL_REGRESSION.log','ORIGINAL_REGRESSION.xml','REGRESSION_INPUTS.json']
manifest={}
for name in names:
    src=HERE/name;dst=target/name
    assert src.is_file() and src.resolve().is_relative_to(HERE.resolve())
    dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dst)
    manifest[name]=hashlib.sha256(dst.read_bytes()).hexdigest()
assert manifest['candidate/tools/unified_identity_binding.py']=='a94ffd53a1b0e9d8ea8843f55fdf5543fdf6a5b1410da2f41804bda82220b029'
(target/'ARCHIVE_MANIFEST.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
print('V1_ARCHIVED_ORIGINAL_BYTES')
