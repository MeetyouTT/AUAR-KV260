"""Run the frozen public six-source proof in its own board process."""
import base64
import hashlib
import json
from pathlib import Path
import sys
import time

HERE = Path(__file__).resolve().parent
STAGE = HERE / 'stage_v19_final_06e5'
REPAIR = HERE.parent.parent
sys.path.insert(0, str(REPAIR))
from probe import ssh


REMOTE = r'''
import base64,hashlib,http.client,json,os,pathlib,subprocess,time
root=pathlib.Path('/home/root/aura-board-business-20261030/production-5259eab11e42af13')
def digest(raw):return hashlib.sha256(raw).hexdigest()
def state():
 connection=http.client.HTTPConnection('127.0.0.1',8783,timeout=5)
 try:
  connection.request('GET','/api/state');response=connection.getresponse();raw=response.read(1048577)
  assert response.status==200 and len(raw)<=1048576
  value=json.loads(raw)
 finally:connection.close()
 listening=value['handsfree_dialogue']
 assert value['phase']=='IDLE' and value['playing'] is False
 assert listening['enabled'] is False and listening['state']=='PAUSED' and listening['microphone_open'] is False
 assert value['avatar_display']['visible'] is True
 assert digest((root/'startup/config.json').read_bytes())==STARTUP
 assert pathlib.Path('/proc/sys/kernel/random/boot_id').read_text().strip()==BOOT
 launch=json.loads((root/'runtime/launch.json').read_bytes())
 stat=(pathlib.Path('/proc')/str(launch['pid'])/'stat').read_text().rsplit(')',1)[1].split()
 return dict(observed_mono=time.monotonic(),gtk_pid=launch['pid'],gtk_birth=int(stat[19]),
             phase='IDLE',playing=False,listening_enabled=False,microphone_open=False,native_visible=True)
before=state()
parent=pathlib.Path('/home/root/aura-public-feature-validation-20261031')
assert parent.resolve()==parent and parent.is_dir()
stage=parent/('joint-v19-'+STAGING_SHA[:16])
assert stage.resolve()==stage and not stage.exists()
decoded={}
assert len(PAYLOAD)==19 and set(PAYLOAD)==set(MANIFEST['files'])
for name,item in PAYLOAD.items():
 relative=pathlib.PurePosixPath(name)
 assert not relative.is_absolute() and relative.parts and '..' not in relative.parts
 raw=base64.b64decode(item,validate=True);row=MANIFEST['files'][name]
 assert len(raw)==row['bytes'] and digest(raw)==row['sha256']
 decoded[name]=raw
stage.mkdir(mode=0o700)
for name,raw in decoded.items():
 path=stage/name;path.parent.mkdir(mode=0o700,parents=True,exist_ok=True)
 assert path.resolve()==path and stage in path.parents
 fd=os.open(str(path),os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
 with os.fdopen(fd,'wb') as handle:
  handle.write(raw);handle.flush();os.fsync(handle.fileno())
args=['/usr/bin/python3','-B',str(stage/'arm_public_worker.py')]
paths={
 'runtime-root':root/'runtime/aura','candidate-root':stage/'after',
 'mapping':stage/'source_mapping.v19.json','candidate-manifest':stage/'SOURCE_MANIFEST.json',
 'original-review':stage/'tree/a/b/c/d/review_m03_win_inference/test_delete_boundaries.py',
 'independent-tests':stage/'test_independent_boundaries.py','public-worker':stage/'public_worker.py',
 'output':stage/'ACTUAL_ARM.json','applied-spec':stage/'applied_spec.v19.json',
 'identity-tests':stage/'identity_tests.py','identity-independent':stage/'identity_independent.py',
 'speaker-fixtures':stage/'speaker_fixtures.py','face-fixtures':stage/'face_fixtures.py',
 'identity-adapter':stage/'identity_stdlib_cases.py','memory-regression':stage/'memory_public_regressions.py',
 'startup-config':root/'startup/config.json'}
for name,path in paths.items():args.extend(['--'+name,str(path)])
args.extend(['--candidate-manifest-sha256',CANDIDATE_SHA,'--root-coordinated-slot','root-public-six-source-paused-v19'])
now=state();assert (now['gtk_pid'],now['gtk_birth'])==(before['gtk_pid'],before['gtk_birth'])
process=subprocess.run(args,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,timeout=150,
                       preexec_fn=lambda:os.nice(10))
after=state();assert (after['gtk_pid'],after['gtk_birth'])==(before['gtk_pid'],before['gtk_birth'])
output=paths['output'];result=json.loads(output.read_bytes()) if output.exists() else None
print(json.dumps(dict(stage=str(stage),staging_manifest_sha256=STAGING_SHA,before=before,after=after,
 process_exit_code=process.returncode,stdout=process.stdout,stderr=process.stderr,result=result,
 production_sources_written=False,production_private_database_opened=False)))
'''


def main():
    raw_manifest = (STAGE / 'STAGING_MANIFEST.json').read_bytes()
    assert hashlib.sha256(raw_manifest).hexdigest() == 'b1852f02161221f631b7a0489c22a885a9e5518d904ef116f3300b641f9bb363'
    manifest = json.loads(raw_manifest)
    assert manifest['case_count'] == 92 and len(manifest['files']) == 19
    assert manifest['composition_input_manifest_sha256'] == '06e5ced57c55b0ef551424c37b08c1a9bd5f43217af98c8a6f9170c1cc597f91'
    assert manifest['files']['arm_public_worker.py']['sha256'] == '10ae4c0f696d4ae332ff8c09c19c6a4668494d809ae09a1643e6fe86b74f52b2'
    assert manifest['files']['SOURCE_MANIFEST.json']['sha256'] == '7ad9bb44686f86068ff61e89865eb0333785287ca1949bbdcc4cfe138bd1ef4f'
    payload = {}
    for name, row in manifest['files'].items():
        path = STAGE / name
        assert path.resolve() == path and STAGE in path.parents
        raw = path.read_bytes()
        assert len(raw) == row['bytes'] and hashlib.sha256(raw).hexdigest() == row['sha256']
        payload[name] = base64.b64encode(raw).decode('ascii')
    values = dict(PAYLOAD=payload, MANIFEST=manifest,
        STAGING_SHA=hashlib.sha256(raw_manifest).hexdigest(),
        STARTUP=manifest['baseline_startup_sha256'], BOOT='bebd3e7d-e984-4517-8cbb-211df7f1c6dc',
        CANDIDATE_SHA=manifest['files']['SOURCE_MANIFEST.json']['sha256'])
    source = '\n'.join(key + '=' + repr(value) for key, value in values.items()) + '\n' + REMOTE
    result = json.loads(ssh('python3 -B -', source, timeout=210))
    output = HERE / ('ACTUAL_ARM_ROOT_' + str(time.time_ns()) + '.json')
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    proof = result.get('result') or {}
    print(json.dumps(dict(file=str(output), stage=result['stage'], exit_code=result['process_exit_code'],
        stderr=result['stderr'], **{key:proof.get(key) for key in
        ('status','tests','failures','errors','temporary_stores_removed','new_threads_remaining')})))
    if result['process_exit_code'] != 0 or proof.get('status') != 'PASS' or proof.get('tests') != 92:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
