"""Root's serial, public-only JPEG component measurement on the current board."""
import base64
import hashlib
import json
from pathlib import Path
import sys
import time

HERE = Path(__file__).resolve().parent
REPAIR = HERE.parent
sys.path.insert(0, str(REPAIR))
from probe import ssh

PACKAGE_SHA = 'e8fe7d20923d131177e5c5f51cff9d7723727941fd7b23b9f17c3ca0f6ab2cb3'

REMOTE = r'''
import base64,hashlib,http.client,json,os,pathlib,subprocess,time
root=pathlib.Path(SPEC['target'])
def state():
 assert pathlib.Path('/proc/sys/kernel/random/boot_id').read_text().strip()==SPEC['boot_id']
 assert hashlib.sha256((root/'startup/config.json').read_bytes()).hexdigest()==SPEC['startup_sha256']
 for role in ('supervisor','gtk','camera'):
  expected=MAPPING[role];p=pathlib.Path('/proc')/str(expected['pid'])
  fields=(p/'stat').read_text().rsplit(')',1)[1].split()
  assert int(fields[19])==expected['birth_ticks']
  assert hashlib.sha256((p/'cmdline').read_bytes()).hexdigest()==expected['command_sha256']
 c=http.client.HTTPConnection('127.0.0.1',8783,timeout=5)
 try:
  c.request('GET','/api/state');response=c.getresponse();raw=response.read(1048577)
  assert response.status==200 and len(raw)<=1048576;v=json.loads(raw)
 finally:c.close()
 h=v['handsfree_dialogue']
 return dict(observed_mono=time.monotonic(),phase=v['phase'],playing=v['playing'],
             listening_enabled=h['enabled'],microphone_open=h['microphone_open'],
             native_visible=v['avatar_display']['visible'],native_frames=v['avatar_display']['frames'])
before=state()
assert before['phase']=='IDLE' and before['playing'] is False
assert before['listening_enabled'] is False and before['microphone_open'] is False and before['native_visible'] is True
parent=pathlib.Path('/home/root/aura-public-jpeg-screen-20261031')
assert parent.resolve()==parent;parent.mkdir(mode=0o700,exist_ok=True)
stage=parent/PACKAGE_SHA[:16];assert stage.resolve()==stage and not stage.exists()
assert set(PAYLOAD)==set(MANIFEST['files'])
decoded={}
for name,value in PAYLOAD.items():
 relative=pathlib.PurePosixPath(name);assert not relative.is_absolute() and '..' not in relative.parts
 raw=base64.b64decode(value,validate=True);assert hashlib.sha256(raw).hexdigest()==MANIFEST['files'][name]
 decoded[name]=raw
stage.mkdir(mode=0o700)
for name,raw in decoded.items():
 path=stage/name;path.parent.mkdir(mode=0o700,parents=True,exist_ok=True)
 assert path.resolve()==path and stage in path.parents
 fd=os.open(str(path),os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
 with os.fdopen(fd,'wb') as handle:
  handle.write(raw);handle.flush();os.fsync(handle.fileno())
command=['/usr/bin/python3','-B',str(stage/'worker.py'),'--frames','60',
         '--logical-capture-fps','15','--opencv-threads','1','--order','AB']
process=subprocess.run(command,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,
                       timeout=300,preexec_fn=lambda:os.nice(10))
assert len(process.stdout)<2097152 and len(process.stderr)<65536
report=json.loads(process.stdout)
after=state()
print(json.dumps(dict(stage=str(stage),package_sha256=PACKAGE_SHA,probe_nice=10,
 before=before,after=after,startup_sha256=SPEC['startup_sha256'],
 process_exit_code=process.returncode,stderr=process.stderr,result=report)))
'''


def main():
    raw = (HERE / 'PACKAGE_MANIFEST.json').read_bytes()
    assert hashlib.sha256(raw).hexdigest() == PACKAGE_SHA
    manifest = json.loads(raw)
    payload = {}
    for name, pin in manifest['files'].items():
        path = HERE / name
        assert path.resolve() == path and HERE in path.parents
        content = path.read_bytes()
        assert hashlib.sha256(content).hexdigest() == pin
        payload[name] = base64.b64encode(content).decode('ascii')
    evidence = REPAIR / 'release_v21_asr2_display_candidate/asr2_display_evidence'
    spec_raw = (evidence / 'spec.json').read_bytes()
    mapping_raw = (evidence / 'source_mapping.json').read_bytes()
    assert hashlib.sha256(spec_raw).hexdigest() == '8dcd958d07de22f996d5f406ab399cdf51e252b1cbd209fac9fdbc6cae8d87a7'
    assert hashlib.sha256(mapping_raw).hexdigest() == 'bff1b76381914cfa070c617e21ce091e8b97a8b7062f408c842cbcf03bc5dee2'
    values = dict(PAYLOAD=payload, MANIFEST=manifest, PACKAGE_SHA=PACKAGE_SHA,
                  SPEC=json.loads(spec_raw), MAPPING=json.loads(mapping_raw))
    source = '\n'.join(key + '=' + repr(value) for key, value in values.items()) + '\n' + REMOTE
    result = json.loads(ssh('python3 -B -', source, timeout=330))
    output = HERE / ('ACTUAL_ARM_' + str(time.time_ns()) + '.json')
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    report = result['result']
    print(json.dumps(dict(file=str(output), exit_code=result['process_exit_code'],
        status=report.get('status'), comparison=report.get('comparison'), stderr=result['stderr'])))
    if result['process_exit_code'] != 0 or report.get('status') != 'PASS':
        raise SystemExit(1)


if __name__ == '__main__':
    main()
