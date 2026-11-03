#!/usr/bin/env python3
"""Continue from the observed active candidate, with the corrected socket probe."""
import datetime
import hashlib
import json
import shutil
from pathlib import Path
from prepare_board_actions import wire

ROOT = Path(__file__).resolve().parents[1]


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    original = Path((ROOT / 'evidence/BOARD_VALIDATION_RUN').read_text().strip())
    diagnostic = (original / '19-start-diagnostic.diagnose.output').read_text()
    assert '"srcversion": "9BDC942A6014BCCBD1DCB78"' in diagnostic
    assert '"device_exists": true' in diagnostic and '"socket_exists": true' in diagnostic
    prepared = json.loads((original / 'preparation.json').read_text())
    run = ROOT / 'evidence' / (datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ') + '-board-continuation')
    run.mkdir(parents=True, exist_ok=False)
    (run / 'action_sources').mkdir()
    shutil.copy2(str(original / 'collect_serial.py'), str(run / 'collect_serial.py'))
    fixed = '''def wait_manager(candidate):
 import socket,time
 for unused in range(100):
  if manager_pid()>0:
   s=socket.socket(socket.AF_UNIX,socket.SOCK_SEQPACKET)
   ret=s.connect_ex('/tmp/dfx-mgrd.socket');s.close()
   if ret==0:manager_guard(candidate);return
  time.sleep(.1)
 raise RuntimeError('SEQPACKET manager startup did not become ready')
'''
    prefix = (original / 'action_sources/07-official-functional.dpu_query.py').read_text().split("gate(", 1)[0] + fixed
    ready = prefix + '''gate('9BDC942A6014BCCBD1DCB78','kv260-benchmark-b4096')
snapshot('BEFORE')
wait_manager(True)
assert watches()==5
print('READY_CHECK '+json.dumps({'pid':manager_pid(),'exe':os.readlink('/proc/%d/exe'%manager_pid()),'kernel_watches':watches(),'protocol':'SOCK_SEQPACKET'}),flush=True)
snapshot('AFTER')
'''
    phase = '20-ready-check'
    (run / 'action_sources' / (phase + '.ready.py')).write_text(ready)
    (run / (phase + '.commands.json')).write_text(json.dumps([{'id': 'ready', 'command': wire(ready), 'timeout': 180}], indent=2) + '\n')
    ordered = [phase]
    for phase in prepared['ordered_phases'][prepared['ordered_phases'].index('07-official-functional'):]:
        manifest = json.loads((original / (phase + '.commands.json')).read_text())
        new_manifest = []
        for item in manifest:
            code = (original / 'action_sources' / (phase + '.' + item['id'] + '.py')).read_text()
            anchor = "exec(compile(s,str(p),'exec'))\n"
            assert code.count(anchor) == 1
            code = code.replace(anchor, anchor + fixed)
            if phase == '14-restore-service':
                stop = "subprocess.run(['systemctl','stop','dfx-mgr.service'],check=True);assert manager_pid()==0"
                assert code.count(stop) == 1
                code = code.replace(stop,
                    "subprocess.run(['systemctl','kill','--kill-who=main','--signal=SIGINT','dfx-mgr.service'],check=True)\n" + stop)
            (run / 'action_sources' / (phase + '.' + item['id'] + '.py')).write_text(code)
            item['command'] = wire(code)
            new_manifest.append(item)
        (run / (phase + '.commands.json')).write_text(json.dumps(new_manifest, indent=2) + '\n')
        ordered.append(phase)
    prepared.update({
        'run': str(run), 'ordered_phases': ordered, 'continuation_of': str(original),
        'reason': 'The original readiness probe used SOCK_STREAM for a SOCK_SEQPACKET service; no failed app operation is retried.',
        'candidate_binary_unchanged': True,
        'manifest_hashes': {p.name: sha(p) for p in run.glob('*.commands.json')},
        'source_hashes': {str(p.relative_to(run)): sha(p) for p in (run / 'action_sources').iterdir()},
        'collector_sha256': sha(run / 'collect_serial.py'),
        'graceful_candidate_stop': 'SIGINT is handled by the unchanged vendor main; it flushes the stdio log before service restoration.'
    })
    (run / 'transfer_candidate.py').write_bytes((original / 'transfer_candidate.py').read_bytes())
    (run / 'preparation.json').write_text(json.dumps(prepared, indent=2) + '\n')
    (ROOT / 'evidence/BOARD_CONTINUATION_RUN').write_text(str(run) + '\n')
    print(json.dumps({'run': str(run), 'phases': len(ordered), 'candidate_sha256': prepared['candidate']['sha256']}))


if __name__ == '__main__':
    main()
