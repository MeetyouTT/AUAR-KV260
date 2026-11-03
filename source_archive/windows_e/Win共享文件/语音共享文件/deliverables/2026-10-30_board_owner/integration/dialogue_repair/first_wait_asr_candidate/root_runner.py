"""Root serial public-ASR probe transport; does not change production settings."""
import argparse
import base64
import hashlib
import json
from pathlib import Path
import sys
import time

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parents[4]
sys.path.insert(0, str(PROJECT / 'deliverables/2026-10-18_board_dialogue'))
from board_ssh import ssh

REMOTE = r'''
import base64,hashlib,http.client,json,pathlib,subprocess,time
def get(port):
 c=http.client.HTTPConnection('127.0.0.1',port,timeout=3)
 try:
  c.request('GET','/health');r=c.getresponse();raw=r.read(1048577)
  assert r.status==200 and len(raw)<=1048576
  return json.loads(raw)
 finally:c.close()
root=pathlib.Path('/home/root/aura-board-business-20261030/production-5259eab11e42af13')
assert hashlib.sha256((root/'startup/config.json').read_bytes()).hexdigest()==EXPECTED
boot=pathlib.Path('/proc/sys/kernel/random/boot_id').read_text().strip()
unit=dict(x.split('=',1) for x in subprocess.check_output(['/bin/systemctl','show','aura-avatar-ui.service','-p','MainPID','-p','ActiveState'],text=True).splitlines() if '=' in x)
assert unit['ActiveState']=='active'
ui=int(unit['MainPID'])
health=get(8790)
camera=health.get('pid')
if type(camera) is not int or camera<2:
 print(json.dumps(dict(status='CAMERA_PID_FIELD_NOT_AVAILABLE',numeric_top_fields={k:v for k,v in health.items() if k in ('pid','camera_pid','process_id') and type(v) is int})))
else:
 def birth(pid):
  raw=(pathlib.Path('/proc')/str(pid)/'stat').read_text()
  return int(raw[raw.rfind(')')+2:].split()[19])
 directory=pathlib.Path('/home/root/aura-public-asr-thread-abba-20261031')/FILES[0]['sha256'][:16]
 assert not directory.parent.is_symlink() and not directory.is_symlink()
 directory.mkdir(mode=0o700,parents=True,exist_ok=True)
 for item in FILES:
  assert item['name'] in ('probe_asr_abba.py','board_asr.py')
  raw=base64.b64decode(item['base64']);assert hashlib.sha256(raw).hexdigest()==item['sha256']
  target=directory/item['name'];assert not target.is_symlink()
  if target.exists():assert target.read_bytes()==raw
  else:
   with target.open('xb') as out:out.write(raw)
 args=['python3','-B',str(directory/'probe_asr_abba.py'),'--boot-id',boot,'--ui-pid',str(ui),'--ui-birth',str(birth(ui)),
       '--camera-pid',str(camera),'--camera-birth',str(birth(camera)),'--candidate',str(directory/'board_asr.py'),
       '--candidate-sha256',FILES[1]['sha256'],'--startup-sha256',EXPECTED]
 if RUN:args.append('--run')
 p=subprocess.run(args,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,timeout=340)
 try:value=json.loads(p.stdout)
 except Exception:value=dict(status='PROBE_OUTPUT_INVALID',exit_code=p.returncode)
 value.update(root_transport_metadata_only=True,probe_sha256=FILES[0]['sha256'],candidate_sha256=FILES[1]['sha256'])
 print(json.dumps(value))
'''

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--probe-sha256', required=True)
    parser.add_argument('--run', action='store_true')
    args = parser.parse_args()
    sources = [('probe_asr_abba.py', HERE / 'probe_asr_abba.py', args.probe_sha256),
               ('board_asr.py', HERE / 'after/board/runtime/audio/board_asr.py',
                'e7af12834461fbb9582dc8ac0c63792569c61d7a56beba5f799f4616b858f447')]
    files = []
    for name, path, expected in sources:
        raw = path.read_bytes()
        assert hashlib.sha256(raw).hexdigest() == expected
        files.append(dict(name=name, sha256=expected, base64=base64.b64encode(raw).decode()))
    spec = json.loads((HERE.parent.parent / 'production_business_acceptance/spec.json').read_text(encoding='utf-8'))
    header = 'EXPECTED=' + repr(spec['startup_sha256']) + '\nFILES=' + repr(files) + '\nRUN=' + repr(args.run) + '\n'
    value = json.loads(ssh('python3 -B -', header + REMOTE, timeout=350))
    output = HERE / (('actual_abba_' if args.run else 'actual_inspect_') + args.probe_sha256[:12] + '_' + str(time.time_ns()) + '.json')
    with output.open('x', encoding='utf-8') as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)
        stream.write('\n')
    print(json.dumps(value))
