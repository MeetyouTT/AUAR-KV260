#!/usr/bin/env python3
"""Read-only sign-off supplement for an already completed joint checkpoint."""
import datetime
import hashlib
import json
import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
current = json.loads((ROOT / 'CURRENT_FPGA.json').read_text())
assert current['state'] == 'finished' and current['rc'] == 0, current
implementation = Path(current['evidence']).resolve()
assert ROOT in implementation.parents
checkpoint = implementation / 'joint_routed.dcp'
checkpoint_hash = hashlib.sha256(checkpoint.read_bytes()).hexdigest()
stamp = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')
out = ROOT / 'evidence' / (stamp + '-checkpoint-audit')
out.mkdir()
hashes = {}
for name in ['audit_checkpoint.tcl', 'report_signoff.tcl']:
    data = (ROOT / 'scripts' / name).read_bytes()
    (out / name).write_bytes(data)
    hashes[name] = hashlib.sha256(data).hexdigest()
status = {'state': 'running', 'evidence': str(out), 'implementation': str(implementation),
          'checkpoint': str(checkpoint), 'checkpoint_sha256': checkpoint_hash,
          'script_sha256': hashes, 'board_modified': False, 'design_modified': False}
(out / 'status.json').write_text(json.dumps(status, indent=2) + '\n')
env = os.environ.copy()
env.update(AURA_ADAPT_ROOT=str(ROOT), AURA_ADAPT_OUT=str(out), AURA_ADAPT_CHECKPOINT=str(checkpoint))
argv = ['bash', '--noprofile', '--norc', '-c',
        'source /home/ghmd/Xilinx_2022.2/Vitis/2022.2/settings64.sh; exec vivado -mode batch -source "$1" -log "$2" -journal "$3"',
        'aura-audit', str(out / 'audit_checkpoint.tcl'), str(out / 'vivado.log'), str(out / 'vivado.jou')]
print(json.dumps(status), flush=True)
with (out / 'console.log').open('wb') as log:
    rc = subprocess.call(argv, cwd=out, env=env, stdout=log, stderr=subprocess.STDOUT)
assert hashlib.sha256(checkpoint.read_bytes()).hexdigest() == checkpoint_hash, 'Checkpoint changed during read-only audit'
status.update(state='finished', rc=rc)
(out / 'status.json').write_text(json.dumps(status, indent=2) + '\n')
if rc == 0:
    for name in ['joint_bus_skew.rpt', 'joint_io.rpt', 'joint_binding_properties.tsv']:
        target = implementation / name
        assert not target.exists(), 'Do not overwrite implementation evidence: ' + name
        target.write_bytes((out / name).read_bytes())
    (implementation / 'signoff_audit.json').write_text(json.dumps(status, indent=2) + '\n')
print(json.dumps(status), flush=True)
raise SystemExit(rc)
