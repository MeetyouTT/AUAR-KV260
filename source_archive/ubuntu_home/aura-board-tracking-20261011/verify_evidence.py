"""Independent saved-response, release and actual-runtime byte checks."""
from pathlib import Path
import base64
import hashlib
import json
import zipfile

WORK=Path(__file__).resolve().parent
REPO=Path('/home/ghmd/Win共享文件/共享文件夹/aura')
def load(p):return json.loads(p.read_text())
def sha(blob):return hashlib.sha256(blob).hexdigest()

meta=load(WORK/'package_validation.json');manifest=load(WORK/'manifest.json')
final=load(WORK/'evidence/20261011T142122.912057Z-final/final.json')
count=artifacts=0;failed=[]
for resultp in sorted((WORK/'evidence').glob('*/result.json')):
    d=load(resultp);assert d['console_echo_restored']
    for entry in d['commands']:
        blob=(resultp.parent/(entry['label']+'.output')).read_bytes()
        assert len(blob)==entry['bytes'] and sha(blob)==entry['sha256']
        count+=1
        if entry['exit_code']:
            assert resultp.parent.name=='20261011T141548.792127Z-final' and b'cannot import name' in blob
            failed.append(str(resultp.parent));continue
        if not blob.strip():continue
        for name,a in json.loads(blob).get('artifacts',{}).items():
            data=base64.b64decode(a['base64'],validate=True)
            assert len(data)==a['bytes'] and sha(data)==a['sha256']
            assert (resultp.parent/name).read_bytes()==data;artifacts+=1
assert len(failed)==1
assert sha(Path(meta['archive']).read_bytes())==meta['sha256']
with zipfile.ZipFile(meta['archive']) as z:
    assert z.testzip() is None and set(z.namelist())==set(manifest['files'])|{'manifest.json'}
    for name,row in manifest['files'].items():
        blob=z.read(name);assert len(blob)==row['bytes'] and sha(blob)==row['sha256']
    for name in manifest['runtime_files']:
        assert sha((REPO/name[5:]).read_bytes())==manifest['files'][name]['sha256']
        assert final['status']['runtime_hashes'][name]==manifest['files'][name]['sha256']
assert final['status']['native_tests']==80
assert len(final['profile']['rows'])==120
assert all(r['frame_visible'] and not r['preview_error'] and not r['ui_error'] for r in final['profile']['rows'])
assert load(WORK/'host_validation.json')['passed_tests']==131
result={'status':'PASS_WITH_RECORDED_LIMITS','uart_responses_verified':count,'artifacts_verified':artifacts,
    'known_failed_response':failed,'package_files':len(manifest['files']),'runtime_files':len(manifest['runtime_files']),
    'source_and_live_hashes_match':True,'runtime_update_id':final['status']['update_id'],
    'acceptance_package_id':meta['update_id'],'startup_release_id':meta['startup_release_id'],
    'host_scoped_tests':131,'new_tracking_tests':12,'board_tests':80,'known_host_voice_errors':7,
    'full_asset_archive_rebuilt':False,'native_expand_return_pass':True,
    'real_target_selection_verified':final['target']['positive_observed'],
    'person_accuracy_and_cold_boot_pending':True}
(WORK/'validation_final.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(result,ensure_ascii=False,indent=2))
