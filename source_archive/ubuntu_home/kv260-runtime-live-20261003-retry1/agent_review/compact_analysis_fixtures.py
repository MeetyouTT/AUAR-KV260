"""Archive-format fixtures on copies of the real failed first run; no board access."""
import gzip
import hashlib
import importlib.util
import json
import lzma
from pathlib import Path
import shutil

ROOT=Path('/home/ghmd/kv260-runtime-live-20261003-retry1/agent_review')
OLD=Path('/home/ghmd/kv260-runtime-live-20261003')
source=ROOT/'analyze_live_compact.py'
spec=importlib.util.spec_from_file_location('compact_offline_analyzer',source)
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
out=ROOT/'compact-analysis-fixtures'
out.mkdir(exist_ok=False)
checks=[]

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def check(name,root,integrity,baseline):
    value=module.analyze(root,out/(name+'-analysis'))
    assert value['overall_pass'] is False,'Failed first run must never be a successful experiment'
    assert value['input_integrity']['passed'] is integrity,name
    assert value['baseline_restored'] is baseline,name
    checks.append({'case':name,'passed':True,'overall_pass':value['overall_pass'],
                   'input_integrity':value['input_integrity']['passed'],
                   'baseline_restored':value['baseline_restored']})
    return value

check('original-no-format-default-gzip',OLD,True,True)
for name,form,damage,integrity,baseline in [
    ('explicit-gzip','tar.gz',None,True,True),
    ('explicit-xz','tar.xz',None,True,True),
    ('announced-xz-file-missing','tar.xz','missing',False,False),
    ('selected-xz-file-corrupted','tar.xz','archive',False,False),
    ('xz-raw-member-corrupted','tar.xz','raw',False,False),
    ('unsupported-format','tar.bz2',None,False,False)]:
    fixture=out/(name+'-dataset');fixture.mkdir()
    shutil.copytree(str(OLD/'board_evidence'),str(fixture/'board_evidence'))
    for filename in ['board_evidence_manifest.json','board_evidence.tar.gz','package_manifest.json']:
        shutil.copy2(str(OLD/filename),str(fixture/filename))
    manifest=json.loads((fixture/'board_evidence_manifest.json').read_text())
    manifest['archive_format']=form
    if form=='tar.xz' and damage!='missing':
        compressed=lzma.compress(gzip.decompress((fixture/'board_evidence.tar.gz').read_bytes()),preset=6)
        target=fixture/'board_evidence.tar.xz';target.write_bytes(compressed)
        manifest['archive_bytes']=len(compressed)
        manifest['archive_sha256']=sha(target)
        if damage=='archive':target.write_bytes(compressed+b'fixture damage')
    if damage=='raw':
        target=fixture/'board_evidence/agent_logs/60-restore/000002-restored-query.stdout'
        target.write_bytes(target.read_bytes()+b'\n')
    (fixture/'board_evidence_manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    check(name,fixture,integrity,baseline)
frozen=ROOT/'analyze_live.py'
assert sha(frozen)=='f20d8620ec2c2b3385f6c5d3e395f1f268d886962f11321df572b94be4ebcbdc'
result={'scope':'Host fixture copies only; the dataset is the FAILED first experiment',
        'passed':True,'compact_source_sha256':sha(source),'original_frozen_sha256':sha(frozen),
        'checks':checks}
(ROOT/'COMPACT_ANALYSIS_FIXTURE_REVIEW.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))
